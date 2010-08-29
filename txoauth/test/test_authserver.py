"""
Tests for txOAuth authentication servers.
"""
from txoauth.authserver import interfaces, cred

from twisted.trial.unittest import TestCase
from twisted.cred.portal import IRealm
from twisted.web2.iweb import IOldRequest

from zope.interface import implements


IDENTIFIER, SECRET = "spam", "eggs"
BOGUS_IDENTIFIER, BOGUS_SECRET = "parrot", "dead"
URL = "eggs"


urlFactory = cred.SimpleCallbackURLFactory(**{IDENTIFIER: URL})


class ClientTestCase(TestCase):
    def test_interface(self):
        self.assertTrue(interfaces.IClient.implementedBy(cred.Client))


    def _genericMemoizationTest(self, identifier, expectedURL):
        c = cred.Client(identifier, urlFactory)
        v = {"old": c._url, "actual": None} # please backport nonlocal
        d = c.getCallbackURL()

        @d.addCallback
        def testMemoization(url):
            self.assertNotEqual(v["old"], url)
            v["actual"] = url # please, please backport nonlocal
            return c.getCallbackURL()
        @d.addCallback
        def testMemoized(url):
            self.assertNotEqual(v["old"], url)
            self.assertEqual(v["actual"], url)

        return d


    def test_memoization_simple(self):
        self._genericMemoizationTest(IDENTIFIER, URL)


    def test_memoization_missingURL(self):
        self._genericMemoizationTest(BOGUS_IDENTIFIER, None)



class SimpleCallbackURLFactoryTestCase(TestCase):
    def setUp(self):
        self.empty = cred.SimpleCallbackURLFactory()
        self.withURLs = cred.SimpleCallbackURLFactory(spam="eggs")


    def test_interface(self):
        self.assertTrue(interfaces.ICallbackURLFactory
                        .implementedBy(cred.SimpleCallbackURLFactory))


    def _genericFactoryTest(self, factory, identifier, expectedURL):
        d = factory.get(identifier)
        @d.addCallback
        def cb(url):
            self.assertEquals(url, expectedURL)
        return d


    def test_empty(self):
        self._genericFactoryTest(self.empty, IDENTIFIER, None)


    def test_registeredURL(self):
        self._genericFactoryTest(urlFactory, IDENTIFIER, URL)


    def test_missingURL(self):
        self._genericFactoryTest(urlFactory, BOGUS_IDENTIFIER, None)



class ClientRealmTestCase(TestCase):
    def test_interface(self):
        self.assertTrue(IRealm.implementedBy(cred.ClientRealm))


    def _genericTest(self, identifier=IDENTIFIER, mind=None,
                     requestedInterfaces=(interfaces.IClient,),
                     expectedURL=URL):
        r = cred.ClientRealm(urlFactory)

        d = r.requestAvatar(identifier, mind, *requestedInterfaces)

        @d.addCallback
        def interfaceCheck(client):
            self.assertTrue(interfaces.IClient.providedBy(client))
            return client.getCallbackURL()

        @d.addCallback
        def callbackURLCheck(url):
            self.assertEquals(url, expectedURL)

        return d


    def test_simple(self):
        self._genericTest()


    def test_missingURL(self):
        self._genericTest(identifier="parrot", expectedURL=None)


    def test_multipleInterfaces(self):
        self._genericTest(requestedInterfaces=(interfaces.IClient, object()))


    def test_badInterface(self):
        r = cred.ClientRealm(urlFactory)
        self.assertRaises(NotImplementedError,
                          r.requestAvatar, "spam", None, object())



class ClientIdentifierTestCase(TestCase):
    def setUp(self):
        self.credentials = cred.ClientIdentifier(IDENTIFIER)


    def test_interface(self):
        self.assertTrue(interfaces.IClientIdentifier
                        .implementedBy(cred.ClientIdentifier))


    def test_simple(self):
        self.assertEqual(self.credentials.identifier, IDENTIFIER)


    def test_identifierImmutability(self):
        def mutate():
            self.credentials.identifier = BOGUS_IDENTIFIER
        self.assertRaises(AttributeError, mutate)


    def test_identifierImmutability_sameIdentifier(self):
        """
        Tests that you are not allowed to mutate, even if it wouldn't actually
        change anything.
        """
        def mutate():
            self.credentials.identifier = self.credentials.identifier
        self.assertRaises(AttributeError, mutate)



class ClientIdentifierSecretTestCase(ClientIdentifierTestCase):
    def setUp(self):
        self.credentials = cred.ClientIdentifierSecret(IDENTIFIER, SECRET)


    def test_interface_withSecret(self):
        self.assertTrue(interfaces.IClientIdentifierSecret
                        .implementedBy(cred.ClientIdentifierSecret))


    def test_simple(self):
        self.assertEqual(self.credentials.secret, SECRET)


    def test_secretImmutability(self):
        def mutate():
            self.credentials.secret = self.credentials.secret
        self.assertRaises(AttributeError, mutate)


    def test_secretImmutability_sameSecret(self):
        """
        Tests that you are not allowed to mutate, even if it wouldn't actually
        change anything.
        """
        def mutate():
            self.credentials.secret = self.credentials.secret
        self.assertRaises(AttributeError, mutate)



class MockRequest(object):
    implements(IOldRequest)

    def __init__(self, authorizationHeader=None, args=None):
        self.args = args or {}
        if authorizationHeader is not None:
            self._identifier, self._secret = (authorizationHeader
                                              .decode("base64").split(":"))
        else:
            self._identifier = self._secret = ""

    def getUser(self):
        return self._identifier


    def getPassword(self):
        return self._secret



class MockRequestTestCase(TestCase):
    def test_simple_nothing(self):
        r = MockRequest()

        self.assertEqual(r.getUser(), "")
        self.assertEqual(r.getPassword(), "")


    def test_simple_authorizationHeader(self):
        r = MockRequest(("%s:%s" % (IDENTIFIER, SECRET)).encode("base64"))

        self.assertEqual(r.getUser(), IDENTIFIER)
        self.assertEqual(r.getPassword(), SECRET)


    def test_bogusInput_missingPassword(self):
        self.assertRaises(Exception, MockRequest, IDENTIFIER.encode("base64"))


    def test_bogusInput_notBase64(self):
        self.assertRaises(Exception, MockRequest, IDENTIFIER)


authHeader = ("%s:%s" % (IDENTIFIER, SECRET)).encode("base64")
simpleAuthHeaderRequest = MockRequest(authHeader)

simpleURLEncodedRequest = MockRequest(args={"client_id": IDENTIFIER})

requestArguments = {"client_id": IDENTIFIER, "client_secret": SECRET}
simpleURLEncodedRequestWithSecret = MockRequest(args=requestArguments)

emptyRequest = MockRequest()

requestArguments = args={"client_secret": SECRET}
secretButNoIdentifierRequest = MockRequest(args=requestArguments)


requestArgs = {
    "grant_type": "authorization_code",
    "client_id": "s6BhdRkqt3",
    "code": "i1WsRn1uB1",
    "redirect_uri":"https%3A%2F%2Fclient%2Eexample%2Ecom%2Fcb"
}
authHeader = "czZCaGRSa3F0MzpnWDFmQmF0M2JW"
firstSpecificationRequest = MockRequest(authHeader, requestArgs)

requestArgs = {
    "grant_type": "authorization_code",
    "client_id": "s6BhdRkqt3",
    "client_secret": "gX1fBat3bV",
    "code": "i1WsRn1uB1",
    "redirect_uri":"https%3A%2F%2Fclient%2Eexample%2Ecom%2Fcb"
}
secondSpecificationRequest = MockRequest(args=requestArgs)

class ClientCredentialsExtractionTestCase(TestCase):
    def test_simple_authorizationHeader(self):
        c = cred._extractClientCredentials(simpleAuthHeaderRequest)

        self.assertTrue(interfaces.IClientIdentifierSecret.providedBy(c))
        self.assertTrue(interfaces.IClientIdentifier.providedBy(c))


    def test_simple_urlEncoded_identifierOnly(self):
        c = cred._extractClientCredentials(simpleURLEncodedRequest)

        self.assertFalse(interfaces.IClientIdentifierSecret.providedBy(c))
        self.assertTrue(interfaces.IClientIdentifier.providedBy(c))


    def test_simple_urlEncoded_identifierAndSecret(self):
        c = cred._extractClientCredentials(simpleURLEncodedRequestWithSecret)

        self.assertTrue(interfaces.IClientIdentifierSecret.providedBy(c))
        self.assertTrue(interfaces.IClientIdentifier.providedBy(c))


    def test_broken_noIdentifierOrSecret(self):
        self.assertRaises(TypeError,
                          cred._extractClientCredentials,
                          emptyRequest)


    def test_broken_SecretNoIdentifier(self):
        self.assertRaises(TypeError,
                          cred._extractClientCredentials,
                          secretButNoIdentifierRequest)


    def test_simple_fromSpecification_first(self):
        """
        Tests for a mocked version of the Authorization header example from
        the specification.
        """
        c = cred._extractClientCredentials(firstSpecificationRequest)

        self.assertTrue(interfaces.IClientIdentifierSecret.providedBy(c))
        self.assertTrue(interfaces.IClientIdentifier.providedBy(c))


    def test_simple_fromSpecification_second(self):
        """
        Tests for a mocked version of the example from the specification
        without an authorization header.
        """
        c = cred._extractClientCredentials(secondSpecificationRequest)

        self.assertTrue(interfaces.IClientIdentifierSecret.providedBy(c))
        self.assertTrue(interfaces.IClientIdentifier.providedBy(c))



class ClientIdentifierAdaptationTestCase(TestCase):
    def test_specificationRequests_first(self):
        c = interfaces.IClientIdentifier(firstSpecificationRequest)
        self.assertTrue(interfaces.IClientIdentifier.providedBy(c))


    def test_specificationRequests_second(self):
        c = interfaces.IClientIdentifier(secondSpecificationRequest)
        self.assertTrue(interfaces.IClientIdentifier.providedBy(c))



class ClientIdentifierSecretAdaptationTestCase(TestCase):
    def test_specificationRequests_first(self):
        c = interfaces.IClientIdentifierSecret(firstSpecificationRequest)
        self.assertTrue(interfaces.IClientIdentifierSecret.providedBy(c))


    def test_specificationRequests_second(self):
        c = interfaces.IClientIdentifierSecret(secondSpecificationRequest)
        self.assertTrue(interfaces.IClientIdentifierSecret.providedBy(c))


    def test_noSecretPresent(self):
        self.assertRaises(TypeError,
                          interfaces.IClientIdentifierSecret,
                          simpleURLEncodedRequest)


    def test_noSecretPresent_emptyrequest(self):
        self.assertRaises(TypeError,
                          interfaces.IClientIdentifierSecret,
                          emptyRequest)