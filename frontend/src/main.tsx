import React, { useCallback, useState } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import {
  ClerkProvider,
  SignIn,
  SignOutButton,
  UserButton,
  useAuth,
} from "@clerk/react";
import type { GetAuthToken } from "./api/client";
import "./styles.css";

const configuredPublishableKey =
  import.meta.env.VITE_CLERK_PUBLISHABLE_KEY?.trim();
const publishableKey =
  import.meta.env.PROD && configuredPublishableKey?.startsWith("pk_test_")
    ? ""
    : configuredPublishableKey;

if (import.meta.env.PROD && configuredPublishableKey?.startsWith("pk_test_")) {
  console.warn(
    "Ignoring the Clerk development key in this production build; simulated demo mode is enabled.",
  );
}

function SignInPage({ onContinueAsDemo }: { onContinueAsDemo: () => void }) {
  return (
    <main className="auth-screen">
      <section className="auth-card">
        <div className="brand-lockup">
          <div className="brand-mark">PP</div>
          <div>
            <p className="brand-name">PlantPulse AI</p>
            <p className="brand-caption">MANUFACTURING INTELLIGENCE</p>
          </div>
        </div>
        <h1>Sign in to PlantPulse</h1>
        <p>Authenticate to access manufacturing analytics.</p>
        <SignIn />
        <div className="demo-divider"><span>or</span></div>
        <button
          className="demo-entry-button"
          onClick={onContinueAsDemo}
          type="button"
        >
          Explore simulated demo
        </button>
        <p className="demo-entry-caption">
          Sample data only. No account or backend connection required.
        </p>
      </section>
    </main>
  );
}

function ClerkApplication() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const getAuthToken: GetAuthToken = useCallback(() => getToken(), [getToken]);
  const [continueAsDemo, setContinueAsDemo] = useState(false);

  if (continueAsDemo) {
    return <App getAuthToken={async () => null} demoMode />;
  }
  if (!isLoaded) {
    return <main className="auth-screen" role="status">Loading authentication…</main>;
  }
  if (!isSignedIn) {
    return <SignInPage onContinueAsDemo={() => setContinueAsDemo(true)} />;
  }

  const accountControls = (
    <div className="account-controls">
      <UserButton />
      <SignOutButton>
        <button className="sign-out-button" type="button">Sign out</button>
      </SignOutButton>
    </div>
  );
  return <App getAuthToken={getAuthToken} accountControls={accountControls} />;
}

const root = ReactDOM.createRoot(document.getElementById("root")!);
root.render(
  <React.StrictMode>
    {publishableKey ? (
      <ClerkProvider publishableKey={publishableKey}>
        <ClerkApplication />
      </ClerkProvider>
    ) : import.meta.env.DEV ? (
      <App getAuthToken={async () => null} demoMode />
    ) : (
      <App getAuthToken={async () => null} demoMode />
    )}
  </React.StrictMode>,
);
