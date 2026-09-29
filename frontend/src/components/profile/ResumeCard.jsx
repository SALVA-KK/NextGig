import React, { useState, useEffect, useRef } from 'react';
import ProfileSection from './ProfileSection';
import { resumeService } from '../../services/resumeService';
import { studentProfileService } from '../../services/studentProfileService';

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

export default function ResumeCard({ onProfileUpdate, currentProfile }) {
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [viewLoading, setViewLoading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [message, setMessage] = useState(null);

  // AI Resume Parsing States
  const [parsing, setParsing] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState({
    skills: [],
    qualification_name: '',
    institution: '',
  });
  const [newSkillText, setNewSkillText] = useState('');
  const [savingSuggestions, setSavingSuggestions] = useState(false);

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

  const handleParseAI = async () => {
    setMessage(null);
    setParsing(true);
    try {
      const data = await resumeService.parseResumeAI();
      setAiSuggestions({
        skills: Array.isArray(data.skills) ? data.skills : [],
        qualification_name: data.qualification_name || '',
        institution: data.institution || '',
      });
      setShowReviewModal(true);
    } catch (err) {
      console.error('[ResumeCard] handleParseAI error:', err);
      setMessage({
        type: 'error',
        text: err.message || 'Could not parse the resume. Please try again or fill in your profile manually.',
      });
    } finally {
      setParsing(false);
    }
  };

  const handleSaveSuggestions = async () => {
    setMessage(null);
    setSavingSuggestions(true);
    try {
      const existingSkills = Array.isArray(currentProfile?.skills) ? currentProfile.skills : [];
      const suggestedSkills = Array.isArray(aiSuggestions?.skills) ? aiSuggestions.skills : [];

      const existingLowerSet = new Set(existingSkills.map((s) => String(s).trim().toLowerCase()));
      const mergedSkills = [...existingSkills];

      suggestedSkills.forEach((skill) => {
        const trimmed = String(skill || '').trim();
        if (trimmed && !existingLowerSet.has(trimmed.toLowerCase())) {
          mergedSkills.push(trimmed);
          existingLowerSet.add(trimmed.toLowerCase());
        }
      });

      const payload = {
        skills: mergedSkills,
      };

      if (aiSuggestions.qualification_name && aiSuggestions.qualification_name.trim()) {
        payload.qualification_name = aiSuggestions.qualification_name.trim();
      }

      if (aiSuggestions.institution && aiSuggestions.institution.trim()) {
        payload.institution = aiSuggestions.institution.trim();
      }

      const updatedProfile = await studentProfileService.updateStudentProfile(payload);

      if (typeof onProfileUpdate === 'function') {
        onProfileUpdate(updatedProfile);
      }

      setShowReviewModal(false);
      setMessage({
        type: 'success',
        text: 'Profile details updated successfully from AI suggestions!',
      });
    } catch (err) {
      console.error('[ResumeCard] handleSaveSuggestions error:', err);
      setMessage({
        type: 'error',
        text: err.message || 'Failed to update profile.',
      });
    } finally {
      setSavingSuggestions(false);
    }
  };

  const handleDiscardSuggestions = () => {
    setShowReviewModal(false);
  };

  const handleAddSkill = () => {
    if (!newSkillText.trim()) return;
    const skill = newSkillText.trim();
    if (!aiSuggestions.skills.includes(skill)) {
      setAiSuggestions((prev) => ({
        ...prev,
        skills: [...prev.skills, skill],
      }));
    }
    setNewSkillText('');
  };

  const handleRemoveSkill = (skillToRemove) => {
    setAiSuggestions((prev) => ({
      ...prev,
      skills: prev.skills.filter((s) => s !== skillToRemove),
    }));
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

  const handleView = async () => {
    setMessage(null);
    setViewLoading(true);

    try {
      const response = await resumeService.downloadResumeBlob();
      const mimeType = response.headers['content-type'] || resume?.mime_type || 'application/pdf';
      const blob = new Blob([response.data], { type: mimeType });
      const blobUrl = window.URL.createObjectURL(blob);
      window.open(blobUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60000);
    } catch (err) {
      console.error('[ResumeCard] handleView error:', err);
      setMessage({
        type: 'error',
        text: err.message || 'Failed to view resume file.',
      });
    } finally {
      setViewLoading(false);
    }
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

      // Create temporary anchor tag to download file
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
          <div className={message.type === 'success' ? 'alert-banner alert-success' : 'alert-banner alert-error'} style={{ marginBottom: '16px' }}>
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
              {/* AI Resume Parse Button - VISIBLE ONLY WHEN RESUME IS UPLOADED */}
              <button
                type="button"
                className="btn-primary-sm"
                onClick={handleParseAI}
                disabled={parsing || downloading || deleting}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: '#4f46e5',
                  color: '#ffffff',
                  fontWeight: '600',
                }}
              >
                {parsing ? (
                  <>
                    <svg className="animate-spin" width="16" height="16" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                    </svg>
                    <span>Reading your resume...</span>
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                    </svg>
                    <span>Parse resume with AI</span>
                  </>
                )}
              </button>

              <button
                type="button"
                className="btn-secondary-sm"
                onClick={handleView}
                disabled={parsing || downloading || viewLoading || deleting}
              >
                {viewLoading ? 'Opening...' : 'View'}
              </button>

              <button
                type="button"
                className="btn-secondary-sm"
                onClick={handleDownload}
                disabled={parsing || downloading || viewLoading || deleting}
              >
                {downloading ? 'Downloading...' : 'Download'}
              </button>

              <button
                type="button"
                className="btn-secondary-sm"
                onClick={() => {
                  setMessage(null);
                  if (fileInputRef.current) fileInputRef.current.click();
                }}
                disabled={parsing || downloading || deleting}
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
                disabled={parsing || downloading || deleting}
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

        {/* AI Resume Suggestions Review Modal */}
        {showReviewModal && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
            <div className="bg-white border border-slate-200 rounded-2xl shadow-xl w-full max-w-xl p-6 sm:p-8 space-y-6 my-8">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">✨</span>
                    <h3 className="text-lg font-extrabold text-slate-900">
                      AI Resume Suggestions
                    </h3>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Review and edit the AI-extracted details below before saving them to your profile. Nothing is saved until you click <strong>Save to Profile</strong>.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleDiscardSuggestions}
                  className="text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-5 border-t border-b border-slate-100 py-5">
                {/* 1. Skills Field */}
                <div className="space-y-2">
                  <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700">
                    Detected Skills
                  </label>
                  <div className="flex flex-wrap gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200 min-h-[48px] items-center">
                    {aiSuggestions.skills.length > 0 ? (
                      aiSuggestions.skills.map((skill, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200"
                        >
                          {skill}
                          <button
                            type="button"
                            onClick={() => handleRemoveSkill(skill)}
                            className="hover:text-indigo-900 font-extrabold text-xs ml-1"
                          >
                            ×
                          </button>
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-amber-700 font-medium italic">
                        Couldn't detect this — fill in manually
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2 pt-1">
                    <input
                      type="text"
                      value={newSkillText}
                      onChange={(e) => setNewSkillText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddSkill();
                        }
                      }}
                      placeholder="Add a skill..."
                      className="flex-1 px-3 py-2 text-xs rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleAddSkill}
                      className="px-3 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs transition-colors"
                    >
                      Add
                    </button>
                  </div>
                </div>

                {/* 2. Qualification Name Field */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700">
                    Qualification Name / Degree
                  </label>
                  <input
                    type="text"
                    value={aiSuggestions.qualification_name}
                    onChange={(e) =>
                      setAiSuggestions((prev) => ({
                        ...prev,
                        qualification_name: e.target.value,
                      }))
                    }
                    placeholder="Couldn't detect this — fill in manually"
                    className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-300 bg-white text-slate-900 placeholder:text-amber-700 placeholder:italic placeholder:font-medium focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                  {currentProfile?.qualification_name &&
                    String(currentProfile.qualification_name).trim() !== String(aiSuggestions.qualification_name || '').trim() && (
                      <p className="text-xs text-slate-500 font-medium pt-0.5">
                        Current: <span className="font-semibold text-slate-700">{currentProfile.qualification_name}</span>
                      </p>
                    )}
                </div>

                {/* 3. Institution Field */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700">
                    Institution / University
                  </label>
                  <input
                    type="text"
                    value={aiSuggestions.institution}
                    onChange={(e) =>
                      setAiSuggestions((prev) => ({
                        ...prev,
                        institution: e.target.value,
                      }))
                    }
                    placeholder="Couldn't detect this — fill in manually"
                    className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-300 bg-white text-slate-900 placeholder:text-amber-700 placeholder:italic placeholder:font-medium focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                  {currentProfile?.institution &&
                    String(currentProfile.institution).trim() !== String(aiSuggestions.institution || '').trim() && (
                      <p className="text-xs text-slate-500 font-medium pt-0.5">
                        Current: <span className="font-semibold text-slate-700">{currentProfile.institution}</span>
                      </p>
                    )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleDiscardSuggestions}
                  disabled={savingSuggestions}
                  className="px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-slate-100 hover:bg-slate-200 text-slate-700 transition-all"
                >
                  Discard
                </button>
                <button
                  type="button"
                  onClick={handleSaveSuggestions}
                  disabled={savingSuggestions}
                  className="px-5 py-2.5 rounded-xl font-extrabold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition-all active:scale-95 disabled:opacity-50"
                >
                  {savingSuggestions ? 'Saving to Profile...' : 'Save to Profile'}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </ProfileSection>
  );
}
