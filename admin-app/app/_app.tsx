"use client";

import React from "react";
import { AppProps } from "next/app";
import { useRouter } from "next/navigation";
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "@/authConfig";

// 1. Instantiate the REAL MSAL instance so it has all the correct internal methods (like getLogger)
export const msalInstance = new PublicClientApplication(msalConfig);

// 2. Create a fake workshop user profile
const dummyAccount = {
  homeAccountId: "workshop-123",
  environment: "login.windows.net",
  tenantId: "workshop-tenant",
  username: "student@workshop.local",
  localAccountId: "workshop-123",
  name: "Workshop Attendee"
};

// 3. Hijack MSAL's authentication methods to bypass the login screen 
// and permanently inject the dummy account into your application's state.
msalInstance.getAllAccounts = () => [dummyAccount];
msalInstance.getActiveAccount = () => dummyAccount;
msalInstance.loginRedirect = async () => console.log("Bypassed loginRedirect");
msalInstance.loginPopup = async () => { 
    console.log("Bypassed loginPopup"); 
    return null as any; 
};
msalInstance.logoutRedirect = async () => console.log("Bypassed logout");

export default function MyApp({ Component, pageProps }: AppProps) {
  // We leave the routing as is. The MsalProvider in your other files 
  // will now consume the hijacked instance without crashing!
  return (
    <Component {...pageProps} />
  );
}