interface ImportMetaEnv {
  readonly DEV: boolean;
  readonly PROD: boolean;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_CLERK_PUBLISHABLE_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
