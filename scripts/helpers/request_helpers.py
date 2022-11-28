"""
Request helper functions
"""
from urllib3 import disable_warnings
from requests_toolbelt import sessions
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException


def http_exceptions(func):
    """
    Wrapper function to be used as a decorator with methods invoking requests.

    Each request will be raised_for_status on execution - add any exception
    handlers in this wrapper so they don't have to be written in each method or
    function.

    :param func: The function being decorated
    :return: Result of executing the function via wrapper()
    """
    def wrapper(*args, **kwargs):
        try:
            wrapper_result = func(*args, **kwargs)
        except RequestException as err:
            print(f"Error processing HTTP request: {err}")
            wrapper_result = False
        return wrapper_result
    return wrapper


def create_request_session(host, username, password, tls_verify=True):
    """
    Create a requests session object for WLC RESTCONF operations

    :param host: Host to establish baseurl session
    :param username: Username for basic auth
    :param password: Password for basic auth
    :param tls_verify: Perform TLS validation?
    :return: HTTP Baseurl session object
    """
    def assert_status_hook(response, **kwargs):  # pylint: disable=unused-argument
        """
        This function is bound to the HTTP Session object and will cause
        every request to be raised for status. By decorating functions with
        @http_exceptions defined above, the request will be performed and
        any exception handling can be centralized instead of repeated inside
        every method.

        :param response: Requests response object
        :return: Invoked raised_for_status() method on the response object.
        """
        return response.raise_for_status()

    # Set the base URL for the session
    baseurl = f"https://{host}/restconf/"

    request_session = sessions.BaseUrlSession(base_url=baseurl)
    request_session.verify = tls_verify
    if not tls_verify:
        disable_warnings()

    # Set the headers for RESTCONF JSON
    request_session.headers = {
        "Content-Type": "application/yang-data+json",
        "Accept": "application/yang-data+json"
    }

    # Attach basic auth to the session
    request_session.auth = HTTPBasicAuth(username, password)

    # When a request is performed, raise for status
    request_session.hooks["response"] = [assert_status_hook]

    return request_session
