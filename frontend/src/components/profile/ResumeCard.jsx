import React, { useState, useEffect, useRef } from 'react';
import ProfileSection from './ProfileSection';
import { resumeService } from '../../services/resumeService';

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

export default function ResumeCard() {
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [message, setMessage] = useState(null);

  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchResume();
  }, []);

  const fetchResume = async () => {
    setLoading(true);
    try {
      const data = await resumeService.getResume();
      if (data && data.original_filename) {
        setResume(data);
      } else {
        setResume(null);
      }
    } catch (err) {
      console.error('[ResumeCard] fetchResume error:', err);
      // Not treating empty as a hard error unless network failed
      if (err.message && err.message.toLowerCase().includes('internet')) {
        setMessage({ type: 'error', text: err.message });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    setMessage(null);

    if (!file) return;

    // Check extension
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'pdf' && ext !== 'docx') {
      setMessage({
        type: 'error',
        text: 'Unsupported file format. Please select a PDF (.pdf) or Word document (.docx).',
      });
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setMessage({
        type: 'error',
        text: 'File size exceeds maximum allowed limit of 5 MB.',
      });
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setSelectedFile(file);
  };

  const handleUploadSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!selectedFile) return;

    setMessage(null);
    setUploading(true);

    try {
      const data = await resumeService.uploadResume(selectedFile);
      setResume(data);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setMessage({
        type: 'success',
        text: resume ? 'Resume replaced successfully!' : 'Resume uploaded successfully!',
      });
    } catch (err) {
      console.error('[ResumeCard] handleUploadSubmit error:', err);
      setMessage({
        type: 'error',
        text: err.message || 'Failed to upload resume. Please try again.',
      });
    } finally {
      setUploading(false);
    }
  };

  const handleCancelFileSelect = () => {
    setSelectedFile(null);
    setMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDownload = async () => {
    setMessage(null);
    setDownloading(true);

    try {
      const response = await resumeService.downloadResumeBlob();
      const blob = new Blob([response.data], {
        type: response.headers['content-type'] || 'application/pdf',
      });
      const blobUrl = window.URL.createObjectURL(blob);

      // Create temporary anchor tag to download/open file
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', resume?.original_filename || 'resume.pdf');
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('[ResumeCard] handleDownload error:', err);
      setMessage({
        type: 'error',
        text: err.message || 'Failed to download resume file.',
      });
    } finally {
      setDownloading(false);
    }
  };

  const handleDeleteConfirm = async () => {
    setMessage(null);
    setDeleting(true);

    try {
      await resumeService.deleteResume();
      setResume(null);
      setShowDeleteConfirm(false);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setMessage({
        type: 'success',
        text: 'Resume deleted successfully.',
      });
    } catch (err) {
      console.error('[ResumeCard] handleDeleteConfirm error:', err);
      setMessage({
        type: 'error',
        text: err.message || 'Failed to delete resume.',
      });
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch (e) {
      return dateString;
    }
  };

  return (
    <ProfileSection
      title="Resume & Opportunity Profile"
      description="Upload your resume to showcase your skills, education, projects, and experience to opportunity providers."
    >
      <div className="resume-card-container">
        {/* Feedback Alert Banner */}
        {message && (
          <div className={`alert-banner alert-${message.type}`} style={{ marginBottom: '16px' }}>
            {message.text}
          </div>
        )}

        {loading ? (
          <div className="resume-loading-state" style={{ padding: '16px 0', color: '#64748b' }}>
            <p>Checking resume status...</p>
          </div>
        ) : resume && !selectedFile ? (
          /* STATE 1: Existing Resume Uploaded */
          <div className="resume-details-box">
            <div className="resume-file-info">
              <div className="resume-icon-wrapper">
                <svg
                  width="28"
                  height="28"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
              </div>

              <div className="resume-text-meta">
                <h4 className="resume-filename">{resume.original_filename}</h4>
                <p className="resume-meta-sub">
                  Uploaded: {formatDate(resume.updated_at || resume.uploaded_at)} • {resume.formatted_file_size}
                </p>
              </div>
            </div>

            {/* Resume Action Buttons */}
            <div className="resume-actions-group">
              <button
                type="button"
                className="btn-secondary-sm"
                onClick={handleDownload}
                disabled={downloading || deleting}
              >
                {downloading ? 'Opening File...' : 'View / Download'}
              </button>

              <button
                type="button"
                className="btn-secondary-sm"
                onClick={() => {
                  setMessage(null);
                  if (fileInputRef.current) fileInputRef.current.click();
                }}
                disabled={downloading || deleting}
              >
                Replace
              </button>

              <button
                type="button"
                className="btn-danger-sm"
                onClick={() => {
                  setMessage(null);
                  setShowDeleteConfirm(true);
                }}
                disabled={downloading || deleting}
              >
                Delete
              </button>

              {/* Hidden file input for replacement */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
            </div>
          </div>
        ) : (
          /* STATE 2: Empty State or File Selected for Upload/Replace */
          <div className="resume-upload-box">
            {!selectedFile ? (
              <div className="resume-empty-dropzone">
                <div className="dropzone-icon">
                  <svg
                    width="36"
                    height="36"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="17 8 12 3 7 8"></polyline>
                    <line x1="12" y1="3" x2="12" y2="15"></line>
                  </svg>
                </div>

                <p className="dropzone-title">Upload your student resume</p>
                <p className="dropzone-hint">
                  Supports <strong>PDF</strong> or <strong>DOCX</strong> documents (Maximum <strong>5 MB</strong>)
                </p>

                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    setMessage(null);
                    if (fileInputRef.current) fileInputRef.current.click();
                  }}
                  style={{ width: 'auto', padding: '10px 24px', marginTop: '12px' }}
                >
                  {resume ? 'Select New Resume File' : 'Select Resume File'}
                </button>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
              </div>
            ) : (
              /* File Selected Confirmation Box */
              <div className="selected-file-confirmation">
                <div className="selected-file-info">
                  <div>
                    <p className="selected-filename">{selectedFile.name}</p>
                    <p className="selected-filesize">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                </div>

                <div className="selected-file-actions">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={handleUploadSubmit}
                    disabled={uploading}
                    style={{ width: 'auto', padding: '8px 20px' }}
                  >
                    {uploading ? 'Uploading...' : resume ? 'Confirm Replacement' : 'Upload Resume'}
                  </button>

                  <button
                    type="button"
                    className="btn-secondary-sm"
                    onClick={handleCancelFileSelect}
                    disabled={uploading}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Delete Confirmation Modal / Prompt */}
        {showDeleteConfirm && (
          <div className="modal-overlay" style={{ marginTop: '16px' }}>
            <div className="delete-confirm-box" style={{
              background: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '16px',
              marginTop: '16px'
            }}>
              <h5 style={{ color: '#ef4444', margin: '0 0 8px 0', fontSize: '15px' }}>
                Delete Resume Confirmation
              </h5>
              <p style={{ color: '#cbd5e1', fontSize: '14px', margin: '0 0 14px 0' }}>
                Are you sure you want to delete your uploaded resume? This action will remove your resume document from your opportunity profile.
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={handleDeleteConfirm}
                  disabled={deleting}
                >
                  {deleting ? 'Deleting...' : 'Yes, Delete Resume'}
                </button>
                <button
                  type="button"
                  className="btn-secondary-sm"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProfileSection>
  );
}
