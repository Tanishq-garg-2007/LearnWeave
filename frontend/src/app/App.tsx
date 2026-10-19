import React from "react";
import { ConfirmProvider } from "@/components/ui/ConfirmDialog";

export function App(): JSX.Element {
  return (
    <ConfirmProvider>
      <div>LearnWeave</div>
    </ConfirmProvider>
  );
}

export default App;
