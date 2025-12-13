"use client";

import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Suspense } from "react";
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
  Spin,
  Flex,
} from "antd";
import {
  PlusOutlined,
  SearchOutlined,
  FolderOpenOutlined,
} from "@ant-design/icons";

// 1. UPDATE INTERFACE: Add vi_mongo_id and keep status as string
export interface Document {
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
  status?: string;      // Should be string: "IN_PROGRESS"
  vi_mongo_id?: string; // New field for the deletion ID
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

  // Selected File State
  const [selectedFileName, setSelectedFileName] = useState<string>("");
  const [selectedCollection, setSelectedCollection] = useState<string>("");
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [selectedIsRootBlob, setSelectedIsRootBlob] = useState<string>("");
  const [selectedViId, setSelectedViId] = useState<string | undefined>(undefined);

  const [authorised, setAuthorised] = useState<boolean>(true);
  const [coursePresent, setCoursePresent] = useState<boolean>(true);
  
  const collectionName = params.course;
  const domainName = params.domain;

  const accounts = msalInstance.getAllAccounts();
  const username = accounts?.[0]?.username ?? "";

  const onFileCreated = () => setToggleCreated((v) => !v);
  const onFileDeleted = () => setToggleDeleted((v) => !v);
  const onFileMoved = () => setToggleMoved((v) => !v);
  const onBlobDeleted = () => setToggleBlobDeleted((v) => !v);

  const openUploadModal = () => setShowUploadModal(true);
  const closeUploadModal = () => setShowUploadModal(false);

  // Updated Handler to accept vi_mongo_id
  const handlePressDelete = (
    id: string, 
    collection: string, 
    file: string, 
    version_id: string, 
    is_root_blob: string,
    vi_mongo_id?: string // Accept the ID from the table
  ) => {
    setSelectedFileName(file);
    setSelectedCollection(collection);
    setSelectedDocId(id);
    setSelectedVersionId(version_id);
    setSelectedIsRootBlob(is_root_blob);
    setSelectedViId(vi_mongo_id); // Set it to state
    setShowDeletionPopup(true);
  };

  const handlePressMovement = (
    id: string, collection: string, file: string, version_id: string
  ) => {
    setSelectedFileName(file);
    setSelectedCollection(collection);
    setSelectedDocId(id);
    setSelectedVersionId(version_id);
    setShowMovementPopup(true);
  };

  const handlePressBlobDelete = (
    id: string, collection: string, file: string, version_id: string, is_root_blob: string
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

  // -------------------------------------------------------------------
  // 1. Reusable Fetch Function (UPDATED)
  // -------------------------------------------------------------------
  const fetchDocs = useCallback(async (isPolling = false) => {
    if (!isPolling) setLoading(true);

    try {
      const docRes = await fetch(
        `http://localhost:5000/api/collections/${username}/${collectionName}/${domainName}`
      );
      
      if (docRes.status === 403) { setAuthorised(false); setDocuments([]); return; }
      if (docRes.status === 404) { setCoursePresent(false); setDocuments([]); return; }
      if (!docRes.ok) throw new Error("Failed to fetch docs");

      const docs: Document[] = await docRes.json();

      // Fetch Video Statuses
      const statusRes = await fetch(`http://localhost:5000/api/vi/status/${collectionName}`);
      
      // Define the type of the response map
      type StatusInfo = { status: string; vi_mongo_id: string };
      const statusMap: Record<string, StatusInfo> = statusRes.ok ? await statusRes.json() : {};

      // Merge Logic - FLATTEN THE OBJECT
      const mergedDocs = docs.map((doc) => {
        const videoInfo = statusMap[doc.name];
        
        if (videoInfo) {
          return { 
            ...doc, 
            status: videoInfo.status,        // Assign string to status
            vi_mongo_id: videoInfo.vi_mongo_id // Assign string to new field
          };
        }
        return doc;
      });

      setDocuments(mergedDocs);

    } catch (err) {
      console.error("Error fetching data:", err);
    } finally {
      if (!isPolling) setLoading(false);
    }
  }, [username, collectionName, domainName]);

  useEffect(() => {
    fetchDocs(false);
  }, [fetchDocs, toggleCreated, toggleDeleted, toggleMoved, toggleBlobDeleted]);

  // -------------------------------------------------------------------
  // 3. Polling Logic
  // -------------------------------------------------------------------
  useEffect(() => {
    // This check now works because d.status is a string again
    const hasInProgress = documents.some((d) => d.status === "IN_PROGRESS");
    
    if (hasInProgress) {
      const intervalId = setInterval(() => {
        fetchDocs(true); 
      }, 5000);
      return () => clearInterval(intervalId);
    }
  }, [documents, fetchDocs]);

  const filteredFiles = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return documents;
    return documents.filter((d) => d?.name?.toLowerCase().includes(q));
  }, [searchQuery, documents]);

  if (!coursePresent) return <NotFoundPage />;
  if (!authorised) return <ForbiddenPage />;

  return (
    <main className="min-h-screen bg-gray-100 pt-12 md:pt-16">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
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

        <div style={{ marginTop: 16 }}>
          {loading ? (
            <Flex align="center" justify="center" style={{ minHeight: 240 }}>
              <Spin size="large" />
            </Flex>
          ) : documents.length > 0 ? (
            <FilesTable
              files={filteredFiles}
              collectionName={collectionName}
              domainName={domainName}
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
          vi_mongo_id={selectedViId} // Pass the ID to the popup
        />
      )}

      {/* ... Other Popups remain unchanged ... */}
      
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