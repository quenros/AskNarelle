import { LogLevel } from "@azure/msal-browser";

export const msalConfig = {
    auth: {
        clientId: "e0a0692d-739b-46b0-bc9e-3561f3d44800",
        // SINGLE TENANT: Use your specific Tenant ID (0714...)
        authority: "https://login.microsoftonline.com/0714d781-75cf-4091-80d4-3aacfd1acc4f", // your tenant ID
        
        // Redirect URI: Uses Env Var in Azure, or localhost for dev
        redirectUri: process.env.NEXT_PUBLIC_REDIRECT_URI || "http://localhost:3000/",
    },
    cache: {
        cacheLocation: "sessionStorage",
        storeAuthStateInCookie: false,
    },
    system: {
        loggerOptions: {
            loggerCallback: (level: LogLevel, message: string, containsPii: boolean) => {
                if (containsPii) { return; }
                switch (level) {
                    case LogLevel.Error:
                        console.error(message);
                        return;
                    // Keep logs clean by commenting out info/verbose unless debugging
                    // case LogLevel.Info: console.info(message); return;
                    // case LogLevel.Verbose: console.debug(message); return;
                    // case LogLevel.Warning: console.warn(message); return;
                }
            },
        },
    },
};

export const loginRequest = {
    scopes: ["User.Read", "Directory.Read.All"],
};

export const graphConfig = {
    graphMeEndpoint: "https://graph.microsoft.com/v1.0/me",
};