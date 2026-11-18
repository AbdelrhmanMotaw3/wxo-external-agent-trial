"""Connection-free synthetic data probe for native PII enforcement."""
from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool(description='Return synthetic contact data for the native privacy-control filming test. No real personal data.')
def kai_outage_demo_contact() -> dict:
    """Read clearly synthetic contact fields; native control should redact these."""
    return {'synthetic':True, 'email':'nour.demo@example.test', 'phone':'+20 100 000 0000',
            'demo_identifier':'DEMO-NID-12345678901234'}
