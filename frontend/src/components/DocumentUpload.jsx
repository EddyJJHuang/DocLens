import React, { useState } from 'react';
import { uploadDocument } from '../services/api';

export const DocumentUpload = ({ onUploadSuccess }) => {
    const [isUploading, setIsUploading] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const [progress, setProgress] = useState(0);
    const [statusText, setStatusText] = useState("Drop or choose PDF, MD, HTML");

    const handleFile = async (file) => {
        if (!file) return;

        setIsUploading(true);
        setProgress(0);
        setStatusText(`Uploading ${file.name}...`);
        
        try {
            await uploadDocument(file, (event) => {
                if (event.total) {
                    setProgress(Math.round((event.loaded * 100) / event.total));
                }
            });
            setStatusText("Indexing in background");
            if(onUploadSuccess) onUploadSuccess();
            setTimeout(() => setStatusText("Drop or choose PDF, MD, HTML"), 3000);
        } catch (err) {
            setStatusText(err.response?.data?.detail || `Upload failed: ${err.message}`);
        } finally {
            setIsUploading(false);
            setProgress(0);
        }
    };

    const handleFileChange = async (e) => {
        await handleFile(e.target.files[0]);
        e.target.value = "";
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFile(e.dataTransfer.files[0]);
    };

    return (
        <div 
            className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
            onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
        >
            <input 
                type="file" 
                id="file-upload" 
                style={{display: 'none'}} 
                onChange={handleFileChange}
                disabled={isUploading}
                accept=".pdf,.md,.html,.htm"
            />
            <label htmlFor="file-upload" style={{cursor: 'pointer', display: 'block', width: '100%', height: '100%'}}>
                <div className="upload-icon">↑</div>
                <div className="upload-status">{statusText}</div>
                {isUploading && (
                    <div className="progress-track" aria-label="Upload progress">
                        <div className="progress-fill" style={{ width: `${progress}%` }} />
                    </div>
                )}
            </label>
        </div>
    );
};
