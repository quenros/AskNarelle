"use client";
import React, { useState } from "react";
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "@/authConfig";
import { Modal, Form, Input, Button, Spin, Alert } from "antd";

interface PopupProps {
  onClose: () => void;
  onCollectionCreated: () => void;
}

export const msalInstance = new PublicClientApplication(msalConfig);

const Popup: React.FC<PopupProps> = ({ onClose, onCollectionCreated }) => {
  const [courseCode, setCourseCode] = useState("");
  const [courseName, setCourseName] = useState("");
  const [description, setDescription] = useState("");

  const [isLoading, setIsLoading] = useState(false);
  const [containerExists, setContainerExists] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username || "";

  const handleCourseCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.trim();
    const regex = /^[a-z0-9-]*$/; // allows lowercase, digits, and hyphen (safe for container/index names)
    if (regex.test(value)) {
      setCourseCode(value);
      setErrorMessage("");
    } else {
      setErrorMessage("Course code can contain lowercase letters, numbers, and hyphens.");
    }
  };

  const handleSubmit = async () => {
    try {
      setIsLoading(true);
      setContainerExists(false);
      setErrorMessage("");

      if (!courseCode) {
        setErrorMessage("Course code is required.");
        return;
      }

      // 1) Create Azure AI Search index (same as before)
      
        const resp = await fetch("http://localhost:5000/createindex", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ collectionName: courseCode }),
        });
        if (!resp.ok) {
          setErrorMessage("Failed to create AI search index");
          return;
        }
      

      // 2) Create container + Cosmos course record via your new endpoint
      
        const res = await fetch("http://localhost:5000/vi/courses", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            courseCode,
            courseName,
            description,
            collectionName: courseCode,
            username
          }),
        });

        if (!res.ok) {
          let payload: any = {};
          try {
            payload = await res.json();
          } catch {}

          if (res.status === 409 || payload?.error === "Container already exists") {
            setContainerExists(true);
            setErrorMessage(
              "This course code already exists. Try a different course code."
            );
          } else {
            setErrorMessage(payload?.error || "Failed to create course");
          }
          return;
        }
      

      onCollectionCreated();
      onClose();
    } catch (err) {
      console.error("Error occurred:", err);
      setErrorMessage("An unexpected error occurred. Please try again later.");
    } finally {
      setIsLoading(false);
    }
  };

  const submitDisabled =
    !courseCode || !!errorMessage || isLoading; // username no longer required by /vi/courses

  return (
    <Modal
      open
      centered
      width={560}
      title="Create Course"
      onCancel={isLoading ? undefined : onClose}
      maskClosable={!isLoading}
      destroyOnClose
      footer={[
        <Button key="cancel" onClick={onClose} disabled={isLoading}>
          Cancel
        </Button>,
        <Button
          key="submit"
          type="primary"
          onClick={handleSubmit}
          loading={isLoading}
          disabled={submitDisabled}
        >
          Submit
        </Button>,
      ]}
    >
      <Spin spinning={isLoading} tip="Creating...">
        <Form layout="vertical">
          <Form.Item
            label="Course Code (lowercase letters / numbers / hyphen)"
            validateStatus={errorMessage ? "error" : ""}
          >
            <Input
              value={courseCode}
              onChange={handleCourseCodeChange}
              placeholder="e.g. 1003 or cs1003 or cs-1003"
              autoFocus
              maxLength={64}
            />
          </Form.Item>

          <Form.Item label="Course Name">
            <Input
              value={courseName}
              onChange={(e) => setCourseName(e.target.value)}
              placeholder="e.g. Data Structures and Algorithms"
              maxLength={128}
            />
          </Form.Item>

          <Form.Item label="Description">
            <Input.TextArea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A short summary of the course"
              rows={4}
              maxLength={1000}
              showCount
            />
          </Form.Item>

          {containerExists && (
            <Alert
              type="error"
              showIcon
              message="Duplicate course code"
              description="This course code already exists. Please try a different one."
            />
          )}

          {!!errorMessage && !containerExists && (
            <Alert type="error" showIcon message={errorMessage} />
          )}
        </Form>
      </Spin>
    </Modal>
  );
};

export default Popup;
