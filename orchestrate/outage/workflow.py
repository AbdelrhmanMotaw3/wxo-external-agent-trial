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
    bonus_data_gb: float
    bonus_balance_before_gb: float
    bonus_balance_after_gb: float
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
    bonus_data_gb: float = 0
    bonus_balance_after_gb: float = 0
    invoice_after_egp: float = 0
    summary: str


@flow(name='kai_outage_data_workflow_20261119',
      display_name='Outage Data Compensation Approval',
      description='Review a 20 GB bonus-data proposal, collect a native human decision, provision once and return a receipt and explicit outcome. The invoice is unchanged.',
      input_schema=CaseInput, output_schema=Result, suppress_agent_summarization=False)
def build_outage_credit(aflow: Flow) -> Flow:
    prepare = aflow.tool('kai_outage_prepare_quote', name='prepare',
                         display_name='Verify Evidence and Prepare Bonus Data',
                         input_schema=CaseInput, output_schema=Quote)
    prepare.map_input('case_id', 'flow.input.case_id')

    # KB review is performed by the Copilot before starting this execution flow.
    # Keep the human pause free of preceding agent-thread handoffs. The backend
    # independently revalidates evidence/policy before provisioning.
    approval = aflow.userflow(name='approval', input_schema=Quote,
                             display_name='Human Approval')
    for field in Quote.model_fields:
        approval.map_input(field, 'flow.prepare.output.'+field)
    # Resolve the real tenant user identifier before setting this value. An email
    # is not silently substituted for a wxo-user ID. Preview ignores assignment.
    approver = os.environ.get('KAI_OUTAGE_APPROVER_USER_ID', 'IBMid-698000U0QU')
    if approver:
        approval.assign_to(UserAssignmentPolicy.USER, assignees=json.dumps([approver]))
    else:
        approval.assign_to(UserAssignmentPolicy.FLOW_INITIATOR)
    form = approval.form(name='decision', display_name='Review Bonus Data Compensation',
                         instructions='Review the 20 GB bonus data proposal. The invoice remains 900 EGP. Record your decision to continue.',
                         submit_button_label='Record Decision')
    for name, label in [
        ('case_id', 'Case ID'), ('quote_id', 'Quote ID'),
        ('confirmed_hours', 'Confirmed Outage Hours'),
        ('bonus_data_gb', 'Proposed Bonus Data (GB)'),
        ('bonus_balance_after_gb', 'Compensation Data Balance After Approval (GB)'),
        ('invoice_before_egp', 'Current Invoice (EGP)'),
        ('invoice_after_egp', 'Unchanged Invoice (EGP)'),
        ('policy_version', 'Policy Reference'),
    ]:
        form.field_output_field(name='review_'+name, label=label, value=DataMap(maps=[
            Assignment(target_variable='self.input.value', value_expression='flow.prepare.output.'+name)]))
    form.boolean_input_field(name='approved', label='Decision',
                             single_checkbox=False, required=True,
                             true_label='Approve', false_label='Reject')
    approval.sequence(START, form, END)

    decision = aflow.tool('kai_outage_workflow_decide', name='record_decision',
                          display_name='Record Decision and Provision Bonus Data',
                          input_schema=DecisionInput, output_schema=Result)
    decision.map_input('quote_id', 'flow.prepare.output.quote_id')
    # UserFlow exposes inferred form outputs under their displayed labels.
    # Verified against the native completed task; nested form IDs are not an
    # output contract of the parent UserFlow.
    decision.map_input('approved', 'flow.approval.output["Decision"]')
    # Stricter demo rule: every proposed credit gets a real human task.
    aflow.sequence(START, prepare, approval, decision, END)
    for field in Result.model_fields:
        aflow.map_output(field, 'flow.record_decision.output.'+field)
    return aflow
