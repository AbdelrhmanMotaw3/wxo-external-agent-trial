"""Native human approval. Only case_id is an agent-supplied input."""
import json
import os
from pydantic import BaseModel
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END
from ibm_watsonx_orchestrate.flow_builder.types import UserAssignmentPolicy, Assignment
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap


class CaseInput(BaseModel):
    case_id: str


class Quote(BaseModel):
    case_id: str
    quote_id: str
    credit_egp: float
    invoice_before_egp: float
    invoice_after_egp: float
    confirmed_hours: float
    requires_approval: bool
    policy_version: str


class DecisionInput(BaseModel):
    quote_id: str
    approved: bool


class PolicyReview(BaseModel):
    policy_review: str


class Result(BaseModel):
    status: str
    case_id: str
    quote_id: str
    receipt_id: str = ''
    credit_egp: float = 0
    invoice_after_egp: float = 0


@flow(name='kai_outage_credit_workflow_20261118',
      display_name='Outage credit approval / اعتماد تعويض الانقطاع',
      description='Assess synthetic outage credit, pause for a real human decision, revalidate and post once. Workflow form approval is required even if chat says approved.',
      input_schema=CaseInput, output_schema=Result, suppress_agent_summarization=False)
def build_outage_credit(aflow: Flow) -> Flow:
    prepare = aflow.tool('kai_outage_prepare_quote', name='prepare',
                         display_name='Verify evidence & calculate / التحقق والحساب',
                         input_schema=CaseInput, output_schema=Quote)
    prepare.map_input('case_id', 'flow.input.case_id')

    policy = aflow.agent(name='policy_review', agent='kai_outage_policy_agent_20261118',
                         display_name='Retrieve policy / مراجعة السياسة',
                         message='Search your knowledge source and review this quote against the outage policy. Explain the relevant sections and whether supervisor approval is needed. Return policy_review with the policy ID and sections. Do not post a credit.',
                         input_schema=Quote, output_schema=PolicyReview)
    for field in Quote.model_fields:
        policy.map_input(field, 'flow.prepare.output.'+field)

    approval = aflow.userflow(name='approval', input_schema=Quote,
                             display_name='Human approval / الموافقة البشرية')
    for field in Quote.model_fields:
        approval.map_input(field, 'flow.prepare.output.'+field)
    # Resolve the real tenant user identifier before setting this value. An email
    # is not silently substituted for a wxo-user ID. Preview ignores assignment.
    approver = os.environ.get('KAI_OUTAGE_APPROVER_USER_ID', 'IBMid-698000U0QU')
    if approver:
        approval.assign_to(UserAssignmentPolicy.USER, assignees=json.dumps([approver]))
    else:
        approval.assign_to(UserAssignmentPolicy.FLOW_INITIATOR)
    form = approval.form(name='decision', display_name='Review the credit / راجع التعويض',
                         instructions='Demo only / بيانات تجريبية. Supervisor requested: amotawea@isys.ai. Review the quote and decide; chat approval is insufficient / راجع العرض واختار القرار.',
                         submit_button_label='Record decision / سجّل القرار')
    for name, label in [
        ('case_id', 'Case / الشكوى'), ('quote_id', 'Quote / العرض'),
        ('confirmed_hours', 'Confirmed hours / ساعات الانقطاع'),
        ('credit_egp', 'Credit EGP / التعويض بالجنيه'),
        ('invoice_before_egp', 'Invoice before EGP / الفاتورة قبل التعويض'),
        ('invoice_after_egp', 'Invoice after EGP / الفاتورة بعد التعويض'),
        ('policy_version', 'Policy / السياسة'),
    ]:
        form.field_output_field(name='review_'+name, label=label, value=DataMap(maps=[
            Assignment(target_variable='self.input.value', value_expression='flow.prepare.output.'+name)]))
    form.boolean_input_field(name='approved', label='Your decision / اختار القرار',
                             single_checkbox=False, required=True,
                             true_label='Approve / موافقة', false_label='Reject / رفض')
    approval.sequence(START, form, END)

    decision = aflow.tool('kai_outage_workflow_decide', name='record_decision',
                          display_name='Revalidate & record / التحقق وتسجيل القرار',
                          input_schema=DecisionInput, output_schema=Result)
    decision.map_input('quote_id', 'flow.prepare.output.quote_id')
    decision.map_input('approved', 'flow.approval.decision.output.approved')
    # Stricter demo rule: every proposed credit gets a real human task.
    aflow.sequence(START, prepare, policy, approval, decision, END)
    for field in Result.model_fields:
        aflow.map_output(field, 'flow.record_decision.output.'+field)
    return aflow
