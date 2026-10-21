"""Every station's requests, for recording and the completeness test."""

from jevdemo import dq, er, pii, schema

STATIONS = {
    "dq": dq.requests,
    "er": er.requests,
    "pii": pii.requests,
    "schema": schema.requests,
}
