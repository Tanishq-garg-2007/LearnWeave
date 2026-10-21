import React from "react";
import { cn } from "@/lib/cn";

export interface TabItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  tabs: TabItem[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
  tabListClassName?: string;
  children?: React.ReactNode;
}

export function Tabs({
  tabs,
  value,
  onChange,
  className,
  tabListClassName,
}: TabsProps): JSX.Element {
  const tabRefs = React.useRef<Map<string, HTMLButtonElement>>(new Map());

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    const enabledTabs = tabs.filter((t) => !t.disabled);
    const currentIndex = enabledTabs.findIndex((t) => t.id === tabs[index].id);

    let nextIndex = -1;
    if (e.key === "ArrowRight") {
      e.preventDefault();
      nextIndex = (currentIndex + 1) % enabledTabs.length;
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      nextIndex = (currentIndex - 1 + enabledTabs.length) % enabledTabs.length;
    } else if (e.key === "Home") {
      e.preventDefault();
      nextIndex = 0;
    } else if (e.key === "End") {
      e.preventDefault();
      nextIndex = enabledTabs.length - 1;
    }

    if (nextIndex >= 0) {
      const nextTab = enabledTabs[nextIndex];
      onChange(nextTab.id);
      const buttonEl = tabRefs.current.get(nextTab.id);
      buttonEl?.focus();
    }
  };

  return (
    <div className={cn("w-full", className)}>
      <div
        role="tablist"
        aria-orientation="horizontal"
        className={cn(
          "inline-flex items-center gap-1.5 p-1.5 rounded-full bg-white/70 border border-surface-border shadow-soft backdrop-blur-md",
          tabListClassName
        )}
      >
        {tabs.map((tab, idx) => {
          const isSelected = tab.id === value;
          return (
            <button
              key={tab.id}
              ref={(el) => {
                if (el) tabRefs.current.set(tab.id, el);
                else tabRefs.current.delete(tab.id);
              }}
              role="tab"
              type="button"
              id={`tab-${tab.id}`}
              aria-controls={`tabpanel-${tab.id}`}
              aria-selected={isSelected}
              tabIndex={isSelected ? 0 : -1}
              disabled={tab.disabled}
              onClick={() => onChange(tab.id)}
              onKeyDown={(e) => handleKeyDown(e, idx)}
              className={cn(
                "inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-semibold transition-all select-none",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-1",
                "disabled:opacity-40 disabled:cursor-not-allowed",
                isSelected
                  ? "bg-ink text-white shadow-sm"
                  : "text-muted hover:text-text hover:bg-black/5"
              )}
            >
              {tab.icon && <span className="inline-flex shrink-0">{tab.icon}</span>}
              <span>{tab.label}</span>
              {tab.badge && <span className="inline-flex">{tab.badge}</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default Tabs;
