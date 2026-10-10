import io
import json
import ssl
import unittest
from email.message import Message
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from mimamori_breach.hibp import (
    MAX_RESPONSE_BYTES,
    REQUEST_TIMEOUT,
    USER_AGENT,
    ClientError,
    HibpClient,
    _NoRedirect,
    normalize_email,
)


KEY = "0" * 32
EMAIL = "synthetic+test@example.com"
RECORD = {
    "Name": "ExampleIncident",
    "Title": "Example Service",
    "Domain": "example.com",
    "BreachDate": "2020-01-02",
    "AddedDate": "2020-02-03T12:34:00Z",
    "DataClasses": ["Passwords", "Email addresses"],
    "Description": "Unused remote markup is never rendered.",
}


class Response(io.BytesIO):
    status = 200


class EmailTests(unittest.TestCase):
    def test_normalization_and_idna(self):
        self.assertEqual(normalize_email("  Person+Demo@EXAMPLE.COM  "), "person+demo@example.com")
        self.assertEqual(normalize_email("person@bücher.example"), "person@xn--bcher-kva.example")

    def test_invalid_address_never_echoes_input(self):
        for address in (
            "", "private-marker", "a@@example.com", ".a@example.com",
            "a..b@example.com", "a@-example.com", "a@example_.com",
            "a@example.com/other", "a@localhost", "a\nb@example.com",
            '"a b"@example.com', "日本@example.com", "a" * 65 + "@example.com", None,
        ):
            with self.subTest(address=address):
                with self.assertRaises(ValueError) as caught:
                    normalize_email(address)
                self.assertEqual(str(caught.exception), "Enter a valid email address.")


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client = HibpClient(KEY)
        self.opener = Mock()
        self.client._opener = self.opener

    def reply(self, value):
        body = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
        self.opener.open.return_value = Response(body)

    def http_error(self, status, retry_after=None):
        headers = Message()
        if retry_after is not None:
            headers["Retry-After"] = retry_after
        self.opener.open.side_effect = HTTPError(
            "https://private.invalid/" + EMAIL, status, "private-marker:" + KEY,
            headers, io.BytesIO(b"remote private-marker"),
        )

    def test_success_requests_encoded_full_verified_data(self):
        self.reply([RECORD])
        breaches = self.client.breaches("  SYNTHETIC+TEST@EXAMPLE.COM ")
        self.assertEqual(len(breaches), 1)
        self.assertEqual(breaches[0].title, "Example Service")
        self.assertEqual(breaches[0].data_classes, ["Email addresses", "Passwords"])
        request = self.opener.open.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://haveibeenpwned.com/api/v3/breachedAccount/"
            "synthetic%2Btest%40example.com?truncateResponse=false&includeUnverified=false",
        )
        self.assertEqual(request.get_header("Hibp-api-key"), KEY)
        self.assertEqual(request.get_header("User-agent"), USER_AGENT)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(self.opener.open.call_args.kwargs, {"timeout": REQUEST_TIMEOUT})

    def test_url_special_characters_in_local_part_are_encoded(self):
        self.reply([])
        self.client.breaches("a/b?c#d@example.com")
        request = self.opener.open.call_args.args[0]
        self.assertIn("a%2Fb%3Fc%23d%40example.com?truncateResponse", request.full_url)

    def test_404_is_successful_empty_result(self):
        self.http_error(404)
        self.assertEqual(self.client.breaches(EMAIL), [])

    def test_status_errors_are_classified_and_do_not_echo_sensitive_details(self):
        for status, kind in ((401, "auth"), (403, "auth"), (429, "rate_limit"),
                             (500, "service"), (302, "service"), (400, "service")):
            with self.subTest(status=status):
                self.http_error(status)
                with self.assertRaises(ClientError) as caught:
                    self.client.breaches(EMAIL)
                error = caught.exception
                self.assertEqual(error.kind, kind)
                self.assertNotIn(KEY, str(error))
                self.assertNotIn(EMAIL, str(error))
                self.assertNotIn("private-marker", repr(error))
                self.assertTrue(error.__suppress_context__)

    def test_retry_after_is_numeric_and_bounded(self):
        cases = (("17", 17), ("0", 1), ("9999999999", 86400),
                 ("-1", 300), ("not-a-number", 300), (None, 300), ("9" * 100, 300))
        for header, expected in cases:
            with self.subTest(header=header):
                self.http_error(429, header)
                with self.assertRaises(ClientError) as caught:
                    self.client.breaches(EMAIL)
                self.assertEqual(caught.exception.retry_after, expected)

    def test_network_failure_is_generic(self):
        for original in (URLError("private-marker:" + EMAIL), TimeoutError(KEY),
                         ssl.SSLError("certificate private-marker")):
            with self.subTest(original=type(original).__name__):
                self.opener.open.side_effect = original
                with self.assertRaises(ClientError) as caught:
                    self.client.breaches(EMAIL)
                self.assertEqual(caught.exception.kind, "network")
                self.assertNotIn("private-marker", str(caught.exception))
                self.assertNotIn(KEY, repr(caught.exception))

    def test_redirects_are_refused(self):
        handler = _NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://example.com"))
        actual = HibpClient(KEY)
        self.assertTrue(any(isinstance(handler, _NoRedirect) for handler in actual._opener.handlers))

    def test_invalid_credentials_and_email_never_make_requests(self):
        for key in ("private-marker", KEY + "\r\nInjected: yes", KEY + "0", None):
            with self.subTest(key=key):
                with self.assertRaises(ValueError) as caught:
                    HibpClient(key)
                self.assertNotIn("private-marker", str(caught.exception))
        with self.assertRaises(ValueError):
            self.client.breaches("private-marker")
        self.opener.open.assert_not_called()

    def test_response_size_is_bounded(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status = 200
        response.read.return_value = b" " * (MAX_RESPONSE_BYTES + 1)
        self.opener.open.return_value = response
        with self.assertRaises(ClientError) as caught:
            self.client.breaches(EMAIL)
        self.assertEqual(caught.exception.kind, "invalid_data")
        response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)

    def test_malformed_or_incomplete_responses_fail_without_partial_success(self):
        invalid = [
            b"not-json private-marker", b"\xff", {"error": "private-marker"},
            [{"Name": "Example"}], [RECORD, {"Name": "MissingFields"}],
            [dict(RECORD, DataClasses="Passwords")], [dict(RECORD, DataClasses=[1])],
            [dict(RECORD, BreachDate="2020-02-31")], [dict(RECORD, BreachDate="20200102")],
            [dict(RECORD, AddedDate="2020-02-03")], [dict(RECORD, Title="hidden\ntext")],
            [dict(RECORD, Domain=None)], [RECORD, RECORD], b'[NaN]',
            b'[{"Name":"x","Name":"y"}]',
        ]
        for payload in invalid:
            with self.subTest(payload=repr(payload)[:80]):
                self.reply(payload)
                with self.assertRaises(ClientError) as caught:
                    self.client.breaches(EMAIL)
                self.assertEqual(caught.exception.kind, "invalid_data")
                self.assertNotIn("private-marker", str(caught.exception))

    def test_empty_domain_and_future_optional_fields_are_allowed(self):
        self.reply([dict(RECORD, Domain="", FutureOptionalField={"anything": True})])
        self.assertEqual(self.client.breaches(EMAIL)[0].domain, "")


if __name__ == "__main__":
    unittest.main()
