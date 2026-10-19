import React, { createContext, useContext, useState, useRef, useCallback } from "react";
import { Modal } from "./Modal";
import { Button } from "./Button";

export interface ConfirmOptions {
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  tone?: "danger" | "default";
}

interface ConfirmContextType {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextType | null>(null);

export function ConfirmProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolverRef = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      resolverRef.current = resolve;
      setOptions(opts);
    });
  }, []);

  const handleClose = (result: boolean) => {
    if (resolverRef.current) {
      resolverRef.current(result);
      resolverRef.current = null;
    }
    setOptions(null);
  };

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {options && (
        <Modal
          open={Boolean(options)}
          onClose={() => handleClose(false)}
          title={options.title}
          description={options.description}
          size="sm"
          footer={
            <>
              <Button
                variant="ghost"
                onClick={() => handleClose(false)}
              >
                {options.cancelText || "Cancel"}
              </Button>
              <Button
                variant={options.tone === "danger" ? "danger" : "primary"}
                onClick={() => handleClose(true)}
              >
                {options.confirmText || "Confirm"}
              </Button>
            </>
          }
        >
          {options.description ? null : (
            <p className="text-sm text-muted">Please confirm whether you want to proceed.</p>
          )}
        </Modal>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm(): (options: ConfirmOptions) => Promise<boolean> {
  const context = useContext(ConfirmContext);
  if (!context) {
    throw new Error("useConfirm must be used within a ConfirmProvider");
  }
  return context.confirm;
}

export default ConfirmProvider;
