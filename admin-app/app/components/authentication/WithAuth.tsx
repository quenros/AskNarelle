import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { msalConfig } from "@/authConfig";
import { PublicClientApplication } from "@azure/msal-browser";

const msalInstance = new PublicClientApplication(msalConfig);

const withAuth = <P extends object>(WrappedComponent: React.ComponentType<P>) => {
  const AuthenticatedComponent = (props: any) => {
    const [isClient, setIsClient] = useState(false);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const router = useRouter();

    useEffect(() => {
      // Ensure this only runs on the client
      setIsClient(true);
      const accounts = msalInstance.getAllAccounts();
      if (accounts.length === 0) {
        // User is not signed in, redirect to homepage
        router.push("/");
      } else {
        setIsAuthenticated(true);
      }
    }, [router]);

    // Avoid rendering anything until authentication is checked
    if (!isClient || !isAuthenticated) {
      return null;
    }

    return <WrappedComponent {...props} />;
  };

  return AuthenticatedComponent;
};

export default withAuth;

