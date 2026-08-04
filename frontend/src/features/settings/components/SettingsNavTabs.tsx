/**
 * Apple 风格分栏切换 Tab 组件。
 * 遵循半透明 Glassmorphism 材质与平滑过渡规范。
 */

export interface SettingsTabItem {
  id: string;
  label: string;
  description: string;
}

interface SettingsNavTabsProps {
  tabs: SettingsTabItem[];
  activeTab: string;
  onTabChange: (id: string) => void;
}

export function SettingsNavTabs({ tabs, activeTab, onTabChange }: SettingsNavTabsProps) {
  return (
    <div className="settings-nav-tabs">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={`settings-tab-btn${isActive ? " is-active" : ""}`}
          >
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
