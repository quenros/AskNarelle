import React, { useMemo, useState, useEffect } from "react";
import SignOutButton from "./authentication/SignOutButton";
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "@/authConfig";
import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Layout, Menu, Drawer, Button, Grid, Typography, Space } from "antd";
import {
  MenuOutlined,
  DashboardOutlined,
  BookOutlined,
  HistoryOutlined,
  LogoutOutlined,
} from "@ant-design/icons";

export const msalInstance = new PublicClientApplication(msalConfig);

const { Header } = Layout;
const { useBreakpoint } = Grid;
const { Text } = Typography;

const Navigation: React.FC = () => {
  const pathname = usePathname();
  const screens = useBreakpoint();
  const [menuOpen, setMenuOpen] = useState(false);

  // Normalize selected key to support prefixed routes
  const selectedKey = useMemo(() => {
    if (pathname?.startsWith("/knowledgebase_management")) return "/knowledgebase_management";
    if (pathname?.startsWith("/activity_log")) return "/activity_log";
    return "/";
  }, [pathname]);

  // Close drawer on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const items = [
    {
      key: "/",
      icon: <DashboardOutlined />,
      label: <Link href="/">Dashboard</Link>,
    },
    {
      key: "/knowledgebase_management",
      icon: <BookOutlined />,
      label: <Link href="/knowledgebase_management">Knowledge Base</Link>,
    },
    {
      key: "/activity_log",
      icon: <HistoryOutlined />,
      label: <Link href="/activity_log">Activity Log</Link>,
    },
  ];

  return (
    <nav style={{ position: "fixed", top: 0, width: "100%", zIndex: 1000 }}>
      <AuthenticatedTemplate>
        <Header
          style={{
            display: "flex",
            alignItems: "center",
            paddingInline: 16,
            background: "#fff",
            borderBottom: "1px solid #f0f0f0",
            boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
          }}
        >
          <Link href="/" style={{ textDecoration: "none" }}>
            <Text strong style={{ color: "#2C3463", fontSize: 20, marginRight: 16 }}>
              AskNarelle
            </Text>
          </Link>

          {screens.md ? (
            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
              <Menu
                mode="horizontal"
                selectedKeys={[selectedKey]}
                items={items}
                // no flex:1; keep it compact and right-aligned
                style={{ borderBottom: "none" }}
              />
              <SignOutButton />
            </div>
          ) : (
            <Button
              type="text"
              icon={<MenuOutlined style={{ fontSize: 20, color: "#2C3463" }} />}
              onClick={() => setMenuOpen(true)}
              style={{ marginLeft: "auto" }}
            />
          )}
        </Header>

        {/* Mobile Drawer unchanged */}
        <Drawer
          title={<Text strong style={{ color: "#2C3463", fontSize: 18 }}>AskNarelle</Text>}
          placement="left"
          width={280}
          open={menuOpen}
          onClose={() => setMenuOpen(false)}
          // bodyStyle={{ padding: 0 }}
        >
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={[
              ...items,
              { key: "signout", icon: <LogoutOutlined />, label: <SignOutButton /> },
            ]}
            onClick={() => setMenuOpen(false)}
          />
        </Drawer>
      </AuthenticatedTemplate>

      <UnauthenticatedTemplate>
        <Header
          style={{
            display: "flex",
            alignItems: "center",
            paddingInline: 16,
            background: "#fff",
            borderBottom: "1px solid #f0f0f0",
            boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
          }}
        >
          <Text strong style={{ color: "#2C3463", fontSize: 20 }}>AskNarelle</Text>
        </Header>
      </UnauthenticatedTemplate>
    </nav>
  );
};

export default Navigation;