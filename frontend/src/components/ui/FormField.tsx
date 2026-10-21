import React from "react";
import { cn } from "@/lib/cn";

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  htmlFor: string;
  required?: boolean;
}

export function Label({
  htmlFor,
  required,
  children,
  className,
  ...props
}: LabelProps): JSX.Element {
  return (
    <label
      htmlFor={htmlFor}
      className={cn("block text-xs font-semibold text-text uppercase tracking-wider mb-1.5 select-none", className)}
      {...props}
    >
      {children}
      {required && <span className="text-danger ml-1" aria-hidden="true">*</span>}
    </label>
  );
}

export interface FieldHintProps extends React.HTMLAttributes<HTMLParagraphElement> {
  id: string;
  children: React.ReactNode;
}

export function FieldHint({
  id,
  children,
  className,
  ...props
}: FieldHintProps): JSX.Element {
  return (
    <p
      id={id}
      className={cn("text-xs text-muted mt-1.5", className)}
      {...props}
    >
      {children}
    </p>
  );
}

export interface FieldErrorProps extends React.HTMLAttributes<HTMLParagraphElement> {
  id: string;
  children?: React.ReactNode;
}

export function FieldError({
  id,
  children,
  className,
  ...props
}: FieldErrorProps): JSX.Element | null {
  if (!children) return null;
  return (
    <p
      id={id}
      role="alert"
      className={cn("text-xs font-medium text-danger mt-1.5 flex items-center gap-1", className)}
      {...props}
    >
      {children}
    </p>
  );
}
