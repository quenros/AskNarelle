import React, { useEffect, useState } from "react";

// WORKSHOP BYPASS: We have removed the MSAL instance and the router redirects.
// This simply takes the protected page and renders it immediately for everyone.
const withAuth = <P extends object>(WrappedComponent: React.ComponentType<P>) => {
  const AuthenticatedComponent = (props: any) => {
    const [isClient, setIsClient] = useState(false);

    useEffect(() => {
      // Ensure this only runs on the client to prevent hydration errors
      setIsClient(true);
    }, []);

    if (!isClient) {
      return null;
    }

    // Instantly return the page without checking authentication status!
    return <WrappedComponent {...props} />;
  };

  return AuthenticatedComponent;
};

export default withAuth;