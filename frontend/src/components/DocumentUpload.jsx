import React, { useState } from 'react';
import { uploadDocument } from '../services/api';

export const DocumentUpload = ({ onUploadSuccess }) => {
    const [isUploading, setIsUploading] = useState(false);
    const [statusText, setStatusText] = useState("Drag & Drop or Click to Upload (PDF/MD/HTML)");

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setIsUploading(true);
        setStatusText(`Uploading ${file.name}...`);
        
        try {
            await uploadDocument(file);
            setStatusText("Upload initiated! Indexing in background.");
            if(onUploadSuccess) onUploadSuccess();
            setTimeout(() => setStatusText("Drag & Drop or Click to Upload (PDF/MD/HTML)"), 3000);
        } catch (err) {
            setStatusText(`Upload failed: ${err.message}`);
        } finally {
            setIsUploading(false);
            e.target.value = ""; // Reset target for successive uploads
        }
    };

    return (
        <div className="upload-dropzone" style={{opacity: isUploading ? 0.5 : 1}}>
            <input 
                type="file" 
                id="file-upload" 
                style={{display: 'none'}} 
                onChange={handleFileChange}
                disabled={isUploading}
                accept=".pdf,.md,.html,.htm"
            />
            <label htmlFor="file-upload" style={{cursor: 'pointer', display: 'block', width: '100%', height: '100%'}}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginBottom: '10px'}}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
                <div style={{fontSize: '0.85rem'}}>{statusText}</div>
            </label>
        </div>
    );
};
