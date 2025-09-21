"use client";

import { useEffect, useState, Suspense } from "react";
import { MdDriveFolderUpload } from "react-icons/md";
import Popup from "../components/courses/CollectionPopup";
import CourseCard from "../components/courses/CourseCard";
import DeletionPopup from "../components/courses/DeletionPopup";
import { msalConfig } from "@/authConfig";
import { PublicClientApplication } from "@azure/msal-browser";
import withAuth from "../components/authentication/WithAuth";
import SharePopup from "../components/courses/SharePopup";
import ManageAccessPopup from "../components/courses/ManageAccessPopup";

// Ant Design
import { Typography, Button, Row, Col, Card, Empty, Space, Divider } from "antd";

const { Title, Text } = Typography;

interface Course {
  course_name: string;
  user_type: string;
  username: string;
}

const msalInstance = new PublicClientApplication(msalConfig);

function ManageKnowledgeBase(): JSX.Element {
  const [message, setMessage] = useState<Course[]>([]);
  const [showPopup, setShowPopup] = useState<boolean>(false);
  const [showDeletionPopup, setShowDeletionPopup] = useState<boolean>(false);
  const [collectionCreated, setCollectionCreated] = useState<boolean>(true);
  const [collectionDeleted, setCollectionDeleted] = useState<boolean>(true);
  const [courseShared, setCourseShared] = useState<boolean>(true);
  const [collection, setCollection] = useState<string>("");
  const [shareName, setShareName] = useState<string>("");
  const [showSharePopup, setShowSharePopup] = useState<boolean>(false);
  const [manageCourseAccess, setManageCourseAccess] = useState<string>("");
  const [showManageAccess, setShowManageAccessPopup] = useState<boolean>(false);

  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username;

  const handleCollectionCreated = () => setCollectionCreated(!collectionCreated);
  const handleCollectionDeleted = () => setCollectionDeleted(!collectionDeleted);
  const handleCourseShared = () => setCourseShared(!courseShared);

  const handleButtonClick = () => setShowPopup(true);
  const handleClosePopup = () => setShowPopup(false);

  const handleCloseSharePopup = () => setShowSharePopup(false);
  const handlePressDelete = (courseName: string) => {
    setCollection(courseName);
    setShowDeletionPopup(true);
  };

  const handleManageAccess = (courseName: string) => {
    setManageCourseAccess(courseName);
    setShowManageAccessPopup(true);
  };
  const handleCloseManageAccess = () => setShowManageAccessPopup(false);

  const handleCourseShare = (courseName: string) => {
    setShareName(courseName);
    setShowSharePopup(true);
  };
  const handleCloseDeletionPopup = () => setShowDeletionPopup(false);

  useEffect(() => {
    if (!username) return;
    fetch(`http://localhost:5000/api/collections/${username}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to fetch collections");
        }
        return response.json();
      })
      .then((collections: Course[]) => setMessage(collections))
      .catch((error) => console.error("Error fetching collections:", error));
  }, [collectionCreated, collectionDeleted, username, courseShared]);

  return (
    <main style={{ marginTop: "8vh", padding: 24, background: "#f5f5f5", minHeight: "100vh" }}>
      {/* Header */}
      <Card bordered={false} style={{ marginBottom: 16 }}>
        <Row align="middle" justify="space-between" gutter={[16, 16]}>
          <Col>
            <Space direction="vertical" size={4}>
              <Title level={3} style={{ margin: 0, color: "#2C3463" }}>
                Courses
              </Title>
              <Divider style={{ margin: 0, borderColor: "#2C3463", width: 72 }} />
              <Text type="secondary">Manage your knowledge base collections</Text>
            </Space>
          </Col>
          <Col>
            {message.length > 0 && (
              <Button type="primary" onClick={handleButtonClick}>
                Add New Course
              </Button>
            )}
          </Col>
        </Row>
      </Card>

      {/* Content */}
      {message.length > 0 ? (
      <Row gutter={[8, 8]}>
        {message.map((collection: Course, index: number) => (
          <Col key={index}>
            <CourseCard
              courseName={collection.course_name}
              userType={collection.user_type}
              onCourseDeleted={handlePressDelete}
              onCourseShare={handleCourseShare}
              onManageAccess={handleManageAccess}
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
                <Text strong>Create a folder for the course</Text>
              </Space>
            }
          >
            <Button type="primary" onClick={handleButtonClick}>
              Add New Course
            </Button>
          </Empty>
        </Card>
      )}

      {/* Popups (unchanged logic) */}
      {showManageAccess && (
        <ManageAccessPopup onClose={handleCloseManageAccess} courseName={manageCourseAccess} />
      )}
      {showPopup && <Popup onClose={handleClosePopup} onCollectionCreated={handleCollectionCreated} />}
      {showDeletionPopup && (
        <DeletionPopup
          onClose={handleCloseDeletionPopup}
          onCourseDeleted={handleCollectionDeleted}
          courseName={collection}
          username={username}
        />
      )}
      {showSharePopup && (
        <SharePopup onClose={handleCloseSharePopup} onCourseShared={handleCourseShare} courseName={shareName} />
      )}
    </main>
  );
}

const AuthenticatedManageKnowledgeBase = withAuth(ManageKnowledgeBase);

export default function KnowledgebaseManagementPage(): JSX.Element {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AuthenticatedManageKnowledgeBase />
    </Suspense>
  );
}
