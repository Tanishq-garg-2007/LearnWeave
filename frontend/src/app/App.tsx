import React from "react";
import { ConfirmProvider } from "@/components/ui/ConfirmDialog";
import { ToastProvider } from "@/components/ui/Toast";

export function App(): JSX.Element {
  return (
    <ToastProvider>
      <ConfirmProvider>
        <div>LearnWeave</div>
      </ConfirmProvider>
    </ToastProvider>
  );
}

export default App;
