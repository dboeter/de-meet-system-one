from jevdemo import pii


def test_bsn_uses_the_eleven_check():
    assert pii.bsn_valid("111222333")
    assert not pii.bsn_valid("123456789")


def test_iban_uses_mod_97():
    assert pii.iban_valid("NL91ABNA0417164300")
    assert not pii.iban_valid("NL91ABNA0417164301")


def test_regex_finds_structured_identifiers_only_when_valid():
    assert pii.regex_hits("BSN 111222333, bel 06-12345678") == {"bsn", "phone"}
    assert pii.regex_hits("ordernummer 123456789") == set()
    assert pii.regex_hits("mail naar j.devries@example.nl") == {"email"}
    assert pii.regex_hits("rekening NL91 ABNA 0417 1643 00") == {"iban"}


def test_routing_takes_the_strictest_route():
    assert pii.route({"bsn"}, {}) == "excluded"
    assert pii.route({"email"}, {}) == "masked"
    assert pii.route(set(), {"person_name": 0.6, "health": 0.1}) == "restricted"
    assert pii.route(set(), {"person_name": 0.6, "health": 0.4}) == "excluded"
    assert pii.route(set(), {"person_name": 0.1, "health": 0.1}) == "clear"
