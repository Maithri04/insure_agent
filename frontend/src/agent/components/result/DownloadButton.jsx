import React, { useState } from 'react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import { Button } from '../common/Button';

export const DownloadButton = ({ targetRef, filename = 'Agent_Report.pdf' }) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    if (!targetRef.current) return;
    try {
      setIsDownloading(true);
      const canvas = await html2canvas(targetRef.current, { scale: 2, backgroundColor: '#ffffff' });
      const imgWidth = 210;
      const pageHeight = 297;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      const doc = new jsPDF('p', 'mm', 'a4');
      doc.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, imgWidth, imgHeight);
      doc.save(filename);
    } catch (error) {
      console.error('PDF generation failed', error);
      alert('Failed to generate PDF');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <Button onClick={handleDownload} disabled={isDownloading} variant="primary">
      {isDownloading ? 'Generating PDF...' : 'Download as PDF'}
    </Button>
  );
};
