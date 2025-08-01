base_auth_uri= "https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=13982625832-amp5pmtf70mk1uc13u134bt2phdfd2ot.apps.googleusercontent.com&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar&state=XyRDeRcNFGaa3nBniJUDrz1X86mprH&access_type=offline&prompt=consent"
redirect_uri = 'https://developers.google.com/oauthplayground' # MUST match your OAuth client app config
        # Append redirect_uri (use urlencode in production)
auth_request_uri = base_auth_uri + f'&redirect_uri={redirect_uri}'
print("Please visit the following URL to authorize the application:", auth_request_uri)
