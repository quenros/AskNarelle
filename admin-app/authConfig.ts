// const NEXTJS_APP_CLIENT_ID='ENTER_CLIENT_ID_HERE'
// const NEXTJS_APP_AUTHORITY='https://login.microsoftonline.com/ENTER_TENANT_ID_HERE'

const NEXTJS_APP_CLIENT_ID= '82975238-6638-446b-8096-0cf0619842ea'
// '509f0927-90b2-4261-b44d-1fb9b18c0ae9'


const NEXTJS_APP_AUTHORITY='https://login.microsoftonline.com/d18181a6-ad98-4e2e-a33a-2be9ed593106'

// Config object to be passed to Msal on creation
export const msalConfig = {
    auth: {
        clientId: NEXTJS_APP_CLIENT_ID,
        authority: NEXTJS_APP_AUTHORITY,
        redirectUri: "/",
        postLogoutRedirectUri: "/"
    },
    system: {
        allowNativeBroker: false, // Disables WAM Broker
    }
};

// Add here scopes for id token to be used at MS Identity Platform endpoints.
export const loginRequest = {
    scopes: ["User.Read"]
};

// Add here the endpoints for MS Graph API services you would like to use.
export const graphConfig = {
    graphMeEndpoint: "https://graph.microsoft.com/v1.0/me"
};
