"use client";
import React, { useState } from "react";
import { AccountInfo, PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "@/authConfig";

// Ant Design
import { Modal, Form, Input, Button, Typography, Spin, Alert } from "antd";

interface PopupProps {
  onClose: () => void;
  onCollectionCreated: () => void;
}

export const msalInstance = new PublicClientApplication(msalConfig);

const Popup: React.FC<PopupProps> = ({ onClose, onCollectionCreated }) => {
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [containerExsists, setContainerExsists] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username || "";

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    const regex = /^[a-z0-9]*$/; // lowercase letters & numbers only

    if (regex.test(value)) {
      setInputValue(value);
      setErrorMessage("");
    } else {
      setErrorMessage("Input can only contain lowercase letters and numbers.");
    }
  };

  const handleSubmit = async () => {
    try {
      setIsLoading(true);
      setContainerExsists(false);

      // Step 1: create index
      const indexResponse = await fetch("http://localhost:5000/createindex", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ collectionName: inputValue }),
      });

      if (!indexResponse.ok) {
        setErrorMessage("Failed to create AI search index");
        return;
      }

      // Step 2: create collection
      const collectionResponse = await fetch(
        "http://localhost:5000/api/createcollection",
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ collectionName: inputValue, username }),
        }
      );

      if (!collectionResponse.ok) {
        try {
          const errorData = await collectionResponse.json();
          if (errorData.error === "Container already exsists") {
            setContainerExsists(true);
            setErrorMessage(
              "This course code is already in the database. Try again with a different course code."
            );
          } else {
            setErrorMessage("Failed to create course");
          }
        } catch {
          setErrorMessage("Failed to create course");
        }
        return;
      }

      // success
      onCollectionCreated();
      onClose();
    } catch (error) {
      console.error("Error occurred:", error);
      setErrorMessage("An unexpected error occurred. Please try again later.");
    } finally {
      setIsLoading(false);
    }
  };

  const submitDisabled =
    !inputValue || Boolean(errorMessage) || isLoading || !username;

  return (
    <Modal
      open
      centered
      width={520}
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
            label="Course Code (Number Only)"
            validateStatus={errorMessage ? "error" : ""}
          >
            <Input
              value={inputValue}
              onChange={handleInputChange}
              placeholder="e.g. 1003"
              autoFocus
              maxLength={64}
            />
          </Form.Item>

          {containerExsists && (
            <Alert
              type="error"
              showIcon
              message="Duplicate course code"
              description="This course code already exists. Please try a different one."
            />
          )}
        </Form>
      </Spin>
    </Modal>
  );
};

export default Popup;
