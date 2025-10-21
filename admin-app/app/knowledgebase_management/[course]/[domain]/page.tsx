"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "@/authConfig";

import DocumentPopup from "../../../components/course_files/DocumentPopup";
import FileDeletionPopup from "../../../components/course_files/FileDeletionPopup";
import FileMovementPopup from "../../../components/course_files/FileMovementPopup";
import BlobDeletionPopup from "../../../components/course_files/BlobDeletionPopup";
import FilesTable from "../../../components/course_files/FilesTable";
import withAuth from "../../../components/authentication/WithAuth";
import NotFoundPage from "../../../components/authentication/404";
import ForbiddenPage from "../../../components/authentication/403";

import {
  Typography,
  Space,
  Button,
  Input,
  Empty,
  Spin,
  App,
  Flex,
} from "antd";
import {
  PlusOutlined,
  SearchOutlined,
  FolderOpenOutlined,
} from "@ant-design/icons";

interface Document {
  _id: string;
  name: string;
  url: string;
  version_id: string;
  blob_name: string;
  domain: string;
  date_str: string;
  time_str: string;
  in_vector_store: string;
  is_root_blob: string;
  course_name: string;
}

const { Title, Text } = Typography;
const msalInstance = new PublicClientApplication(msalConfig);

function Fileslist({
  params,
}: {
  params: { domain: string; course: string };
}): JSX.Element {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [toggleCreated, setToggleCreated] = useState<boolean>(false);
  const [toggleDeleted, setToggleDeleted] = useState<boolean>(false);
  const [toggleMoved, setToggleMoved] = useState<boolean>(false);
  const [toggleBlobDeleted, setToggleBlobDeleted] = useState<boolean>(false);

  const [searchQuery, setSearchQuery] = useState<string>("");

  const [showDeletionPopup, setShowDeletionPopup] = useState<boolean>(false);
  const [showMovementPopup, setShowMovementPopup] = useState<boolean>(false);
  const [showBlobDeletionPopup, setShowBlobDeletionPopup] = useState<boolean>(false);

  const [selectedFileName, setSelectedFileName] = useState<string>("");
  const [selectedCollection, setSelectedCollection] = useState<string>("");
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [selectedIsRootBlob, setSelectedIsRootBlob] = useState<string>("");

  const [authorised, setAuthorised] = useState<boolean>(true);
  const [coursePresent, setCoursePresent] = useState<boolean>(true);
  
  const collectionName = params.course;
  const domainName = params.domain;

  const accounts = msalInstance.getAllAccounts();
  const username = accounts?.[0]?.username ?? "";

  // Actions that toggle fetch refresh
  const onFileCreated = () => setToggleCreated((v) => !v);
  const onFileDeleted = () => setToggleDeleted((v) => !v);
  const onFileMoved = () => setToggleMoved((v) => !v);
  const onBlobDeleted = () => setToggleBlobDeleted((v) => !v);

  // Button handlers
  const openUploadModal = () => setShowUploadModal(true);
  const closeUploadModal = () => setShowUploadModal(false);

  const handlePressDelete = (
    id: string,
    collection: string,
    file: string,
    version_id: string,
    is_root_blob: string
  ) => {
    setSelectedFileName(file);
    setSelectedCollection(collection);
    setSelectedDocId(id);
    setSelectedVersionId(version_id);
    setSelectedIsRootBlob(is_root_blob);
    setShowDeletionPopup(true);
  };

  const handlePressMovement = (
    id: string,
    collection: string,
    file: string,
    version_id: string
  ) => {
    setSelectedFileName(file);
    setSelectedCollection(collection);
    setSelectedDocId(id);
    setSelectedVersionId(version_id);
    setShowMovementPopup(true);
  };

  const handlePressBlobDelete = (
    id: string,
    collection: string,
    file: string,
    version_id: string,
    is_root_blob: string
  ) => {
    setSelectedFileName(file);
    setSelectedCollection(collection);
    setSelectedDocId(id);
    setSelectedVersionId(version_id);
    setSelectedIsRootBlob(is_root_blob);
    setShowBlobDeletionPopup(true);
  };

  const closeDeletionPopup = () => setShowDeletionPopup(false);
  const closeMovementPopup = () => setShowMovementPopup(false);
  const closeBlobDeletionPopup = () => setShowBlobDeletionPopup(false);

  // Fetch
  useEffect(() => {
    let abort = false;
    setLoading(true);
    fetch(
      `http://localhost:5000/api/collections/${username}/${collectionName}/${domainName}`
    )
      .then((response) => {
        if (abort) return null;
        if (response.status === 403) {
          setAuthorised(false);
          setDocuments([]);
          return null;
        } else if (response.status === 404) {
          setCoursePresent(false);
          setDocuments([]);
          return null;
        } else if (response.status === 500) {
          throw new Error("Failed to fetch course documents");
        } else {
          return response.json();
        }
      })
      .then((docs: Document[] | null) => {
        if (abort || !docs) return;
        setDocuments(docs);
      })
      .catch((err) => {
        console.error("Error fetching documents:", err);
      })
      .finally(() => {
        if (!abort) setLoading(false);
      });

    return () => {
      abort = true;
    };
  }, [
    toggleCreated,
    toggleDeleted,
    toggleMoved,
    toggleBlobDeleted,
    collectionName,
    domainName,
    username,
  ]);

  const filteredFiles = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return documents;
    return documents.filter((d) => d?.name?.toLowerCase().includes(q));
  }, [searchQuery, documents]);

  // Render gates for 404/403
  if (!coursePresent) return <NotFoundPage />;
  if (!authorised) return <ForbiddenPage />;

  return (
    <main className="min-h-screen bg-gray-100 pt-12 md:pt-16">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
        {/* Header row */}
        <Flex justify="space-between" align="center" wrap>
          <Title level={3} style={{ margin: 0 }}>
            {collectionName}
          </Title>

          {documents.length > 0 && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={openUploadModal}
            >
              Add New File
            </Button>
          )}
        </Flex>

        {/* Search */}
        {documents.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for files"
              prefix={<SearchOutlined />}
              allowClear
              size="middle"
            />
          </div>
        )}

        {/* Content */}
        <div style={{ marginTop: 16 }}>
          {loading ? (
            <Flex align="center" justify="center" style={{ minHeight: 240 }}>
              <Spin size="large" />
            </Flex>
          ) : documents.length > 0 ? (
            <FilesTable
              files={filteredFiles}
              collectionName={collectionName}
              onFileDeleted={handlePressDelete}
              onFileMoved={handlePressMovement}
              onBlobDeleted={handlePressBlobDelete}
            />
          ) : (
            <div className="flex items-center justify-center">
              <div className="bg-white w-full sm:w-4/5 border border-dashed border-[#3F50AD] p-6 rounded-lg text-center">
                <FolderOpenOutlined style={{ fontSize: 36, color: "#2C3463" }} />
                <Space direction="vertical" style={{ width: "100%" }} size="small">
                  <Text strong style={{ fontSize: 16 }}>
                    Upload the materials
                  </Text>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={openUploadModal}
                  >
                    Add New Files
                  </Button>
                </Space>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modals / Popups */}
      {showUploadModal && (
        <DocumentPopup
          onClose={closeUploadModal}
          onFileCreated={onFileCreated}
          collectionName={collectionName}
          domainName={domainName}
          username={username}
        />
      )}

      {showDeletionPopup && (
        <FileDeletionPopup
          fileName={selectedFileName}
          collectionName={selectedCollection}
          id={selectedDocId}
          onFileDeleted={() => {
            onFileDeleted();
            closeDeletionPopup();
          }}
          onClose={closeDeletionPopup}
          domainName={domainName}
          version_id={selectedVersionId}
          is_root_blob={selectedIsRootBlob}
          username={username}
        />
      )}

      {showMovementPopup && (
        <FileMovementPopup
          fileName={selectedFileName}
          collectionName={selectedCollection}
          id={selectedDocId}
          onFileMoved={() => {
            onFileMoved();
            closeMovementPopup();
          }}
          onClose={closeMovementPopup}
          domainName={domainName}
          version_id={selectedVersionId}
          username={username}
        />
      )}

      {showBlobDeletionPopup && (
        <BlobDeletionPopup
          fileName={selectedFileName}
          onBlobDeleted={() => {
            onBlobDeleted();
            closeBlobDeletionPopup();
          }}
          id={selectedDocId}
          collectionName={selectedCollection}
          onClose={closeBlobDeletionPopup}
          domainName={domainName}
          version_id={selectedVersionId}
          is_root_blob={selectedIsRootBlob}
          username={username}
        />
      )}
    </main>
  );
}

const AuthenticatedFilesList = withAuth(Fileslist);

export default function FilePage({
  params,
}: {
  params: { domain: string; course: string };
}): JSX.Element {
  return (
    <Suspense fallback={<Spin style={{ margin: 24 }} />}>
      <AuthenticatedFilesList params={params} />
    </Suspense>
  );
}
