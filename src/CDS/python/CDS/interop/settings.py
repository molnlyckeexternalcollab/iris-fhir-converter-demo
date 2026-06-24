from bs.hapi import Hapi as BSHapi
from bs.patient_view import PatientView as BSPatientView
from bs.order_select import OrderSelect as BSOrderSelect
from bs.order_sign import OrderSign as BSOrderSign

from bp.hapi import Hapi as BPHapi
from bp.patient_view import PatientView as BPPatientView
from bp.order_select import OrderSelect as BPOrderSelect
from bp.order_sign import OrderSign as BPOrderSign

from bo.hapi import Hapi as BOHapi
from bo.fhir import Fhir as BOFhir

CLASSES = {
    'Python.BS.Hapi':        BSHapi,
    'Python.BS.PatientView': BSPatientView,
    'Python.BS.OrderSelect': BSOrderSelect,
    'Python.BS.OrderSign':   BSOrderSign,
    'Python.BP.Hapi':        BPHapi,
    'Python.BP.PatientView': BPPatientView,
    'Python.BP.OrderSelect': BPOrderSelect,
    'Python.BP.OrderSign':   BPOrderSign,
    'Python.BO.Hapi':        BOHapi,
    'Python.BO.Fhir':        BOFhir,
}

PRODUCTIONS = [
{
    "CDSPKG.FoundationProduction": {
        "@Name": "CDSPKG.FoundationProduction",
        "@TestingEnabled": "true",
        "@LogGeneralTraceEvents": "false",
        "Description": "",
        "ActorPoolSize": "1",
        "Item": [
            # --- Business Services ---
            {
                "@Name": "BS.Hapi",
                "@ClassName": "Python.BS.Hapi",
                "@PoolSize": "1",
                "@Enabled": "true",
            },
            {
                "@Name": "BS.PatientView",
                "@ClassName": "Python.BS.PatientView",
                "@PoolSize": "1",
                "@Enabled": "true",
            },
            {
                "@Name": "BS.OrderSelect",
                "@ClassName": "Python.BS.OrderSelect",
                "@PoolSize": "1",
                "@Enabled": "true",
            },
            {
                "@Name": "BS.OrderSign",
                "@ClassName": "Python.BS.OrderSign",
                "@PoolSize": "1",
                "@Enabled": "true",
            },
            # --- Business Processes ---
            {
                "@Name": "BP.Hapi",
                "@ClassName": "Python.BP.Hapi",
                "@PoolSize": "1",
                "@Enabled": "true",
                "@Foreground": "false",
                "@LogTraceEvents": "false",
                "@Schedule": "",
            },
            {
                "@Name": "BP.PatientView",
                "@ClassName": "Python.BP.PatientView",
                "@PoolSize": "1",
                "@Enabled": "true",
                "@Foreground": "false",
                "@LogTraceEvents": "false",
                "@Schedule": "",
            },
            {
                "@Name": "BP.OrderSelect",
                "@ClassName": "Python.BP.OrderSelect",
                "@PoolSize": "1",
                "@Enabled": "true",
                "@Foreground": "false",
                "@LogTraceEvents": "false",
                "@Schedule": "",
            },
            {
                "@Name": "BP.OrderSign",
                "@ClassName": "Python.BP.OrderSign",
                "@PoolSize": "1",
                "@Enabled": "true",
                "@Foreground": "false",
                "@LogTraceEvents": "false",
                "@Schedule": "",
            },
            # --- Business Operations ---
            {
                "@Name": "BO.Hapi",
                "@ClassName": "Python.BO.Hapi",
                "@PoolSize": "1",
                "@Enabled": "true",
            },
            {
                "@Name": "BO.Fhir",
                "@ClassName": "Python.BO.Fhir",
                "@PoolSize": "1",
                "@Enabled": "true",
            },
        ]
    }
}
]
