"use client";

import { Suspense, useEffect, useState } from "react";
import DomainCard from "../../components/domains/DomainCard";
import { useSearchParams } from "next/navigation";
import DomainPopup from "../../components/domains/DomainPopup";
import DomainDeletionPopup from "../../components/domains/DomainDeletionPopup";
import { MdDriveFolderUpload } from "react-icons/md";
import withAuth from "../../components/authentication/WithAuth";
import { msalConfig } from "@/authConfig";
import { PublicClientApplication } from "@azure/msal-browser";
import NotFoundPage from "../../components/authentication/404";
import ForbiddenPage from "../../components/authentication/403";

// Ant Design
import {
  Typography,
  Button,
  Row,
  Col,
  Card,
  Empty,
  Space,
  Divider,
} from "antd";

const { Title, Text } = Typography;

interface Category {
  domain: string;
  usertype: string;
}

const msalInstance = new PublicClientApplication(msalConfig);

function DomainContent({ params }: { params: { course: string } }) {
  const [showPopup, setShowPopup] = useState<boolean>(false);
  const [domainCreated, setDomainCreated] = useState<boolean>(true);
  const [domains, setDomains] = useState<Category[]>([]);
  const [domainDeleted, setDomainDeleted] = useState<boolean>(true);
  const [domainName, setDomainName] = useState<string>("");
  const [showDeletionPopup, setShowDeletionPopup] = useState<boolean>(false);
  const [course, setCourse] = useState<string>("");
  const [authorised, setAuthorised] = useState<boolean>(true);
  const [coursePresent, setCoursePresent] = useState<boolean>(true);

  const searchParams = useSearchParams();
  const collectionName = params.course;

  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username;

  const handleButtonClick = () => setShowPopup(true);
  const handleClosePopup = () => setShowPopup(false);

  const handleDomainCreated = () => setDomainCreated(!domainCreated);
  const handleDomainDeleted = () => setDomainDeleted(!domainDeleted);

  const handlePressDelete = (courseName: string, dName: string) => {
    setCourse(courseName);
    setDomainName(dName);
    setShowDeletionPopup(true);
  };
  const handleCloseDeletionPopup = () => setShowDeletionPopup(false);

  useEffect(() => {
    if (!username) return;

    fetch(`http://localhost:5000/api/collections/${username}/${collectionName}/domains`)
      .then((response) => {
        if (response.status === 403) {
          setAuthorised(false);
          return null;
        } else if (response.status === 404) {
          setCoursePresent(false);
          return null;
        } else if (!response.ok) {
          throw new Error("Failed to fetch course domains");
        }
        return response.json();
      })
      .then((data) => {
        if (data) setDomains(data as Category[]);
      })
      .catch((error) => {
        console.error("Error fetching collections:", error);
      });
  }, [domainCreated, domainDeleted, collectionName, username]);

  return (
    <main style={{ marginTop: "8vh", padding: 24, background: "#f5f5f5", minHeight: "100vh" }}>
      {/* Header */}
      {authorised && coursePresent && (
        <Card bordered={false} style={{ marginBottom: 16 }}>
          <Row align="middle" justify="space-between" gutter={[16, 16]}>
            <Col>
              <Space direction="vertical" size={4}>
                <Title level={3} style={{ margin: 0, color: "#2C3463" }}>
                  Categories
                </Title>
                <Divider style={{ margin: 0, borderColor: "#2C3463", width: 84 }} />
                <Text type="secondary">Manage your course categories</Text>
              </Space>
            </Col>
            <Col>
              {domains?.length > 0 && (
                <Button type="primary" onClick={handleButtonClick}>
                  Add New Category
                </Button>
              )}
            </Col>
          </Row>
        </Card>
      )}

      {/* Content states */}
      {coursePresent ? (
        authorised ? (
          domains?.length > 0 ? (
            <Row gutter={[16, 16]}>
              {domains.map((domain: Category, index: number) => (
                <Col key={index} xs={24} sm={12} md={8} lg={6} xl={6}>
                  <DomainCard
                    courseName={collectionName}
                    domainName={domain.domain}
                    onDomainDeleted={handlePressDelete}
                    user_type={domain.usertype}
                  />
                </Col>
              ))}
            </Row>
          ) : (
            <Card style={{ maxWidth: 900, margin: "48px auto" }}>
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <Space direction="vertical" size={4}>
                    <MdDriveFolderUpload size={40} color="#2C3463" />
                    <Text strong>Create a new category</Text>
                  </Space>
                }
              >
                <Button type="primary" onClick={handleButtonClick}>
                  Add New Category
                </Button>
              </Empty>
            </Card>
          )
        ) : (
          <ForbiddenPage />
        )
      ) : (
        <NotFoundPage />
      )}

      {/* Popups (logic unchanged) */}
      {showPopup && (
        <DomainPopup
          onClose={handleClosePopup}
          onDomainCreated={handleDomainCreated}
          collectionName={collectionName}
        />
      )}
      {showDeletionPopup && (
        <DomainDeletionPopup
          onClose={handleCloseDeletionPopup}
          onCourseDeleted={handleDomainDeleted}
          courseName={collectionName}
          domain={domainName}
        />
      )}
    </main>
  );
}

const AuthenticatedDomainContent = withAuth(DomainContent);

export default function DomainPage({ params }: { params: { course: string } }): JSX.Element {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AuthenticatedDomainContent params={params} />
    </Suspense>
  );
}
