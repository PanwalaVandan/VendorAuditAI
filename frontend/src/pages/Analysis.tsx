import { useState, useEffect, Component, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, FileText, AlertTriangle, Loader2, RefreshCw, Download, FileSpreadsheet, Shield } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { CardSkeleton, SkeletonLoader } from '@/components/ui/TypingIndicator';
import { FindingsSummary, FindingsList } from '@/components/findings';
import apiClient, { getApiErrorMessage } from '@/lib/api';
import { normalizeFinding } from '@/lib/findings';
import type { Document, Finding, AnalysisRun, Severity } from '@/types/api';

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: { type: 'spring' as const, stiffness: 100, damping: 15 },
  },
};

// Finding variants for animated lists (exported for use in child components)
export const findingVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.05, type: 'spring' as const, stiffness: 100 },
  }),
};

// Supported compliance frameworks matching backend FrameworkType
const FRAMEWORKS = [
  { value: 'soc2_tsc', label: 'SOC 2 TSC' },
  { value: 'nist_800_53', label: 'NIST 800-53' },
  { value: 'iso_27001', label: 'ISO 27001' },
  { value: 'cis_controls', label: 'CIS Controls' },
  { value: 'hipaa', label: 'HIPAA' },
  { value: 'pci_dss', label: 'PCI-DSS' },
  { value: 'caiq', label: 'CAIQ (CSA STAR)' },
  { value: 'nist_ai_rmf', label: 'NIST AI RMF' },
  { value: 'ai_risk', label: 'AI Risk Assessment' },
] as const;

type FrameworkType = typeof FRAMEWORKS[number]['value'];

/**
 * Error boundary to catch render crashes in findings components
 * and show a readable error instead of a blank screen.
 */
class FindingsErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; message: string }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, message: '' };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, message: error.message };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 rounded-lg bg-destructive/10 text-destructive border border-destructive/20">
          <p className="font-medium">Failed to render findings</p>
          <p className="text-sm mt-1 text-muted-foreground">{this.state.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * Analysis Page - Document analysis dashboard with findings display.
 * Allows users to select a document, run analysis, and view findings.
 */
export function Analysis() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();

  // Allow vendor/document pages to pre-select a document via ?document_id=...
  const documentIdParam = searchParams.get('document_id') ?? '';
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>(documentIdParam);
  const [selectedFramework, setSelectedFramework] = useState<FrameworkType>('soc2_tsc');

  // Keep the selection in sync if the URL param changes (e.g. browser back/forward)
  useEffect(() => {
    if (documentIdParam) setSelectedDocumentId(documentIdParam);
  }, [documentIdParam]);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState<'csv' | 'pdf' | null>(null);

  // Export findings as CSV or PDF - success state for UI feedback
  const [_exportSuccess, setExportSuccess] = useState<string | null>(null);
  void _exportSuccess; // Used for success notification
  const handleExport = async (format: 'csv' | 'pdf') => {
    if (!selectedDocumentId) return;

    setIsExporting(format);
    setAnalysisError(null);
    setExportSuccess(null);
    try {
      const response = await apiClient.get(`/export/findings/${format}`, {
        params: { document_id: selectedDocumentId },
        responseType: 'blob',
      });

      // Create download link
      const blob = new Blob([response.data], {
        type: format === 'csv' ? 'text/csv' : 'application/pdf',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `findings-${selectedDocumentId.slice(0, 8)}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setExportSuccess(`Successfully exported as ${format.toUpperCase()}`);
      // Clear success message after 3 seconds
      setTimeout(() => setExportSuccess(null), 3000);
    } catch (error) {
      setAnalysisError(getApiErrorMessage(error));
    } finally {
      setIsExporting(null);
    }
  };

  // Fetch documents for dropdown - get all processed documents
  const { data: documentsResponse, isLoading: isLoadingDocuments } = useQuery({
    queryKey: ['documents-for-analysis'],
    queryFn: async () => {
      const response = await apiClient.get('/documents?limit=100');
      return response.data;
    },
  });

  const documents: Document[] = (documentsResponse?.data || []).filter(
    (doc: Document) => doc.status === 'processed' || doc.status === 'analyzed'
  );

  // Fetch findings for selected document using the correct endpoint
  const {
    data: findingsResponse,
    isLoading: isLoadingFindings,
    refetch: refetchFindings,
  } = useQuery({
    queryKey: ['analysis-findings', selectedDocumentId],
    queryFn: async () => {
      const response = await apiClient.get('/analysis/findings', {
        params: { document_id: selectedDocumentId, limit: 100 },
      });
      return response.data;
    },
    enabled: !!selectedDocumentId,
  });

  // Fetch analysis runs for selected document
  const { data: runsResponse } = useQuery({
    queryKey: ['analysis-runs', selectedDocumentId],
    queryFn: async () => {
      const response = await apiClient.get('/analysis/runs', {
        params: { document_id: selectedDocumentId, limit: 10 },
      });
      return response.data;
    },
    enabled: !!selectedDocumentId,
  });

  // Normalize snake_case backend response to camelCase Finding shape
  const findings: Finding[] = (findingsResponse?.data || []).map(normalizeFinding);
  const analysisRuns: AnalysisRun[] = runsResponse?.data || [];
  const latestRun = analysisRuns[0];

  // Run analysis mutation - uses correct backend endpoint
  const runAnalysisMutation = useMutation({
    mutationFn: async ({ documentId, framework }: { documentId: string; framework: FrameworkType }) => {
      // POST /analysis/documents/{document_id}/analyze with { framework, chunk_limit }
      // LLM analysis can take 60-180s depending on document size and provider, so use a long timeout
      const response = await apiClient.post(`/analysis/documents/${documentId}/analyze`, {
        framework,
        chunk_limit: 50,
      }, { timeout: 180000 });
      return response.data;
    },
    onSuccess: () => {
      setAnalysisError(null);
      // Invalidate and refetch analysis data
      queryClient.invalidateQueries({ queryKey: ['analysis-findings', selectedDocumentId] });
      queryClient.invalidateQueries({ queryKey: ['analysis-runs', selectedDocumentId] });
      queryClient.invalidateQueries({ queryKey: ['documents-for-analysis'] });
    },
    onError: (error) => {
      setAnalysisError(getApiErrorMessage(error));
    },
  });

  const handleRunAnalysis = () => {
    if (selectedDocumentId && selectedFramework) {
      runAnalysisMutation.mutate({ documentId: selectedDocumentId, framework: selectedFramework });
    }
  };

  const selectedDocument = documents.find((d) => d.id === selectedDocumentId);

  // Calculate severity counts
  const bySeverity: Record<Severity, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  };

  findings.forEach((finding) => {
    if (finding.severity in bySeverity) {
      bySeverity[finding.severity]++;
    }
  });

  const isAnalyzing = runAnalysisMutation.isPending || latestRun?.status === 'running';

  return (
    <motion.div
      className="p-8"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      {/* Header */}
      <motion.div className="mb-8" variants={itemVariants}>
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold neon-text">
            ANALYSIS<span className="text-primary">ENGINE</span>
          </h1>
          <motion.div
            className="w-2 h-2 rounded-full bg-obsidian-teal"
            animate={{
              scale: [1, 1.3, 1],
              opacity: [0.7, 1, 0.7],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        </div>
        <p className="text-muted-foreground">
          Analyze security documents and review findings
        </p>
      </motion.div>

      {/* Document Selection */}
      <motion.div variants={itemVariants}>
        <Card className="mb-6 glass-panel-liquid">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Document Selection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
              {/* Document Dropdown */}
              <div className="md:col-span-1">
                <label
                  htmlFor="document-select"
                  className="block text-sm font-medium text-muted-foreground mb-2"
                >
                  Select a document
                </label>
                <select
                  id="document-select"
                  value={selectedDocumentId}
                  onChange={(e) => setSelectedDocumentId(e.target.value)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  disabled={isLoadingDocuments}
                >
                  <option value="">
                    {isLoadingDocuments ? 'Loading documents...' : 'Choose a document...'}
                  </option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.filename || doc.originalFilename} ({(doc.document_type || doc.docType)?.toUpperCase() || 'DOC'})
                    </option>
                  ))}
                </select>
              </div>

              {/* Framework Dropdown */}
              <div className="md:col-span-1">
                <label
                  htmlFor="framework-select"
                  className="block text-sm font-medium text-muted-foreground mb-2"
                >
                  <Shield className="h-4 w-4 inline mr-1" />
                  Compliance Framework
                </label>
                <select
                  id="framework-select"
                  value={selectedFramework}
                  onChange={(e) => setSelectedFramework(e.target.value as FrameworkType)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  {FRAMEWORKS.map((fw) => (
                    <option key={fw.value} value={fw.value}>
                      {fw.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button
                  onClick={handleRunAnalysis}
                  disabled={!selectedDocumentId || isAnalyzing}
                  className="flex-1"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Run Analysis
                    </>
                  )}
                </Button>

                {selectedDocumentId && (
                  <Button
                    variant="outline"
                    onClick={() => refetchFindings()}
                    disabled={isLoadingFindings}
                  >
                    <RefreshCw className={`h-4 w-4 ${isLoadingFindings ? 'animate-spin' : ''}`} />
                  </Button>
                )}
              </div>
            </div>

            {/* Selected document info */}
            {selectedDocument && (
              <motion.div
                className="mt-4 p-3 bg-secondary/50 rounded-md"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: 'spring' as const, stiffness: 100 }}
              >
                <div className="flex items-center gap-4 text-sm flex-wrap">
                  <span>
                    <strong>Type:</strong> {(selectedDocument.document_type || selectedDocument.docType)?.toUpperCase() || 'Document'}
                  </span>
                  {(selectedDocument.page_count || selectedDocument.pageCount) !== undefined && (selectedDocument.page_count || selectedDocument.pageCount) !== null && (
                    <span>
                      <strong>Pages:</strong> {selectedDocument.page_count || selectedDocument.pageCount}
                    </span>
                  )}
                  <span>
                    <strong>Status:</strong>{' '}
                    <span
                      className={`font-medium ${
                        selectedDocument.status === 'analyzed' || selectedDocument.status === 'processed'
                          ? 'text-green-600'
                          : selectedDocument.status === 'failed'
                          ? 'text-red-600'
                          : 'text-yellow-600'
                      }`}
                    >
                      {selectedDocument.status?.charAt(0).toUpperCase() +
                        selectedDocument.status?.slice(1)}
                    </span>
                  </span>
                  {latestRun && (
                    <span>
                      <strong>Last Analysis:</strong>{' '}
                      {new Date(latestRun.created_at).toLocaleDateString()} ({latestRun.framework})
                    </span>
                  )}
                </div>
              </motion.div>
            )}

            {/* Error message */}
            <AnimatePresence>
              {analysisError && (
                <motion.div
                  className="mt-4 flex items-center gap-2 p-3 bg-destructive/10 text-destructive rounded-md text-sm"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ type: 'spring' as const, stiffness: 100 }}
                >
                  <AlertTriangle className="h-4 w-4" />
                  {analysisError}
                </motion.div>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>
      </motion.div>

      {/* Analysis Progress */}
      <AnimatePresence>
        {isAnalyzing && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ type: 'spring' as const, stiffness: 100 }}
          >
            <Card className="mb-6 border-primary glass-panel-liquid">
              <CardContent className="py-8">
                <div className="flex flex-col items-center justify-center">
                  <Loader2 className="h-12 w-12 text-primary animate-spin mb-4" />
                  <h3 className="text-lg font-medium mb-2">Analysis in Progress</h3>
                  <p className="text-muted-foreground text-center mb-4">
                    Analyzing document against {FRAMEWORKS.find(f => f.value === selectedFramework)?.label || selectedFramework}...
                  </p>
                  <p className="text-sm text-muted-foreground">
                    This may take 1-2 minutes depending on document size.
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* No document selected state */}
      <AnimatePresence>
        {!selectedDocumentId && !isLoadingDocuments && (
          <motion.div
            variants={itemVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
          >
            <Card className="glass-panel-liquid">
              <CardContent className="flex flex-col items-center justify-center py-16">
                <FileText className="h-16 w-16 text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">Select a Document</h3>
                <p className="text-muted-foreground text-center max-w-md">
                  Choose a processed document from the dropdown above to view existing analysis results or run a
                  new analysis against a compliance framework.
                </p>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading state for findings */}
      <AnimatePresence>
        {selectedDocumentId && isLoadingFindings && !isAnalyzing && (
          <motion.div
            className="space-y-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <CardSkeleton />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <CardSkeleton />
              <CardSkeleton />
            </div>
            <SkeletonLoader lines={5} className="glass-panel-liquid p-6 rounded-2xl" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Analysis Results */}
      <AnimatePresence>
        {selectedDocumentId && !isLoadingFindings && !isAnalyzing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <FindingsErrorBoundary>
            {findings.length > 0 ? (
              <div className="space-y-6">
                {/* Summary Statistics */}
                <motion.div variants={itemVariants}>
                  <FindingsSummary bySeverity={bySeverity} total={findings.length} />
                </motion.div>

                {/* Findings List with Filtering */}
                <motion.div variants={itemVariants}>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold">Findings ({findings.length})</h2>
                    <div className="flex gap-2">
                      <motion.div
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleExport('csv')}
                          disabled={isExporting !== null}
                        >
                          {isExporting === 'csv' ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <FileSpreadsheet className="h-4 w-4 mr-2" />
                          )}
                          Export CSV
                        </Button>
                      </motion.div>
                      <motion.div
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleExport('pdf')}
                          disabled={isExporting !== null}
                        >
                          {isExporting === 'pdf' ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4 mr-2" />
                          )}
                          Export PDF
                        </Button>
                      </motion.div>
                    </div>
                  </div>
                  <FindingsList findings={findings} />
                </motion.div>
              </div>
            ) : (
              <motion.div variants={itemVariants}>
                <Card className="glass-panel-liquid">
                  <CardContent className="flex flex-col items-center justify-center py-16">
                    <AlertTriangle className="h-16 w-16 text-muted-foreground mb-4" />
                    <h3 className="text-lg font-medium mb-2">No Analysis Results</h3>
                    <p className="text-muted-foreground text-center max-w-md mb-4">
                      This document hasn't been analyzed yet, or no findings were detected.
                      Select a compliance framework and click "Run Analysis" to analyze this document.
                    </p>
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <Button onClick={handleRunAnalysis} disabled={isAnalyzing || !selectedDocumentId}>
                        <Play className="h-4 w-4 mr-2" />
                        Run Analysis
                      </Button>
                    </motion.div>
                  </CardContent>
                </Card>
              </motion.div>
            )}
            </FindingsErrorBoundary>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
