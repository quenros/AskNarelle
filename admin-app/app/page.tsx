"use client";
import React, { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  AuthenticatedTemplate,
  UnauthenticatedTemplate,
  useIsAuthenticated,
} from "@azure/msal-react";
import { MdWavingHand } from "react-icons/md";
import SignInButton from "./components/authentication/SignInButton";
import CardDataStats from "./components/dashboard/CardDataStats"; // kept (unused now, but not removed)
import { IoPeople } from "react-icons/io5";
import { BsQuestionCircle } from "react-icons/bs";
import ChartOne from "./components/dashboard/ChartOne";
import ChartTwo from "./components/dashboard/ChartTwo";
import ChartThree from "./components/dashboard/ChartThree";
import ChartFour from "./components/dashboard/ChartFour";
import { msalConfig } from "../authConfig";
import { PublicClientApplication } from "@azure/msal-browser";
import Image from "next/image";

// Ant Design imports
import {
  Row,
  Col,
  Card,
  Statistic,
  Typography,
  Space,
  Skeleton,
  Result,
  Divider,
} from "antd";

const { Title, Text } = Typography;

const msalInstance = new PublicClientApplication(msalConfig);

export default function Home() {
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();

  const [totalUsers, setTotalUsers] = useState<number | 0>();
  const [totalQueries, setTotalQueries] = useState<number | 0>();
  const [username, setUsername] = useState<string | undefined>();
  const [greeting, setGreeting] = useState<string>("");

  useEffect(() => {
    if (isAuthenticated) {
      const accounts = msalInstance.getAllAccounts();
      if (accounts.length > 0) {
        setUsername(accounts[0].username);
      }
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (username) {
      fetch(
        `http://localhost:5000/chats/totalUsers/${username}`
      )
        .then((r) => {
          if (!r.ok) throw new Error("Failed to fetch total users");
          return r.json();
        })
        .then((n: number) => setTotalUsers(n))
        .catch((e) => console.error("Error fetching total users:", e));

      fetch(
        `http://localhost:5000/chats/totalQueries/${username}`
      )
        .then((r) => {
          if (!r.ok) throw new Error("Failed to fetch total queries");
          return r.json();
        })
        .then((n: number) => setTotalQueries(n))
        .catch((e) => console.error("Error fetching total queries:", e));
    }
  }, [username]);

  useEffect(() => {
    const currentHour = new Date().getHours();
    if (currentHour < 12) setGreeting("Good Morning,");
    else if (currentHour < 18) setGreeting("Good Afternoon,");
    else setGreeting("Good Evening,");
  }, []);

  const loading = useMemo(
    () => totalUsers === undefined || totalQueries === undefined,
    [totalUsers, totalQueries]
  );

  return (
    <div>
      <AuthenticatedTemplate>
        {/* Top spacer since your header is fixed ~8vh */}
        <div style={{ marginTop: "8vh", padding: "24px" }}>
          <Card bordered style={{ marginBottom: 16 }}>
            <Space direction="vertical" size={4}>
              <Title level={3} style={{ margin: 0 }}>
                {greeting}
              </Title>
              <Text type="secondary">Dashboard Homepage</Text>
            </Space>
          </Card>

          {/* KPI Row */}
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Card>
                {loading ? (
                  <Skeleton active paragraph={false} />
                ) : (
                  <Space
                    align="center"
                    size="large"
                    style={{ width: "100%", justifyContent: "space-between" }}
                  >
                    <Statistic
                      title="Total Users"
                      value={totalUsers}
                      valueStyle={{ color: "#2C3463" }}
                    />
                    <div
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: 12,
                        background: "#f5f5f5",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <IoPeople size={28} color="#2C3463" />
                    </div>
                  </Space>
                )}
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card>
                {loading ? (
                  <Skeleton active paragraph={false} />
                ) : (
                  <Space
                    align="center"
                    size="large"
                    style={{ width: "100%", justifyContent: "space-between" }}
                  >
                    <Statistic
                      title="Total Queries"
                      value={totalQueries}
                      valueStyle={{ color: "#2C3463" }}
                    />
                    <div
                      style={{
                        width: 56,
                        height: 56,
                        borderRadius: 12,
                        background: "#f5f5f5",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <BsQuestionCircle size={28} color="#2C3463" />
                    </div>
                  </Space>
                )}
              </Card>
            </Col>
          </Row>

          {/* Charts / Empty State */}
          {!loading && totalUsers === 0 ? (
            <Card style={{ marginTop: 16 }}>
              <Result
                status="info"
                title="No usage yet"
                subTitle="Once users start interacting, you’ll see charts and trends here."
              />
            </Card>
          ) : (
            <>
              <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                <Col xs={24} md={12}>
                  <Card title="Usage Over Time">
                    {/* Keep your chart component intact */}
                    <ChartOne />
                  </Card>
                </Col>
                <Col xs={24} md={12}>
                  <Card title="Top Categories">
                    <ChartTwo />
                  </Card>
                </Col>
              </Row>

              <Row gutter={[16, 16]} style={{ marginTop: 16, marginBottom: 16 }}>
                <Col xs={24} md={12}>
                  <Card title="Active Users">
                    <ChartThree />
                  </Card>
                </Col>
                <Col xs={24} md={12}>
                  <Card title="Query Breakdown">
                    <ChartFour />
                  </Card>
                </Col>
              </Row>
            </>
          )}
        </div>
      </AuthenticatedTemplate>

      <UnauthenticatedTemplate>
        {/* Login view */}
        <div
          style={{
            minHeight: "95vh",
            marginTop: "5vh",
            padding: 24,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 24,
          }}
        >
          <div style={{ display: "none" }} className="sm:block" />
          <Row gutter={[24, 24]} align="middle" style={{ width: "100%" }}>
            <Col xs={24} md={14}>
              <div style={{ position: "relative", width: "100%", height: "60vh" }}>
                <Image
                  src="/assets/hive.jpg"
                  alt="My Image"
                  fill
                  style={{ objectFit: "cover", borderRadius: 12 }}
                  priority
                />
              </div>
            </Col>

            <Col xs={24} md={10}>
              <Card>
                <Space direction="vertical" size={8} style={{ width: "100%" }}>
                  <Title level={3} style={{ color: "#3F50AD", margin: 0, textAlign: "center" }}>
                    Admin Site
                  </Title>
                  <Text type="secondary" style={{ display: "block", textAlign: "center" }}>
                    Login
                  </Text>

                  <Divider style={{ margin: "12px 0" }} />

                  <Space align="center" style={{ justifyContent: "center", width: "100%" }}>
                    <Text style={{ fontSize: 16 }}>Hi, Welcome</Text>
                    <MdWavingHand style={{ marginLeft: 6 }} />
                  </Space>

                  <div style={{ display: "flex", justifyContent: "center", marginTop: 8 }}>
                    <SignInButton />
                  </div>
                </Space>
              </Card>
            </Col>
          </Row>
        </div>
      </UnauthenticatedTemplate>
    </div>
  );
}