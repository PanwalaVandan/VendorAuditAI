import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Settings as SettingsIcon,
  FileText,
  Cpu,
  Zap,
  Server,
  CheckCircle,
  XCircle,
  Loader2,
  Eye,
  EyeOff,
  Save,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button, Input, Label } from '@/components/ui';
import apiClient, { getApiErrorMessage } from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExternalParserConfig {
  url: string;
  api_key: string;
}

interface DocumentProcessingSettings {
  provider: 'docling' | 'legacy' | 'external';
  external_parser: ExternalParserConfig | null;
}

interface OrgSettings {
  document_processing: DocumentProcessingSettings;
}

interface TestResult {
  ok: boolean;
  error?: string;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchOrgSettings(): Promise<OrgSettings> {
  const { data } = await apiClient.get<OrgSettings>('/organization/settings');
  return data;
}

async function saveOrgSettings(payload: Partial<OrgSettings>): Promise<OrgSettings> {
  const { data } = await apiClient.patch<OrgSettings>('/organization/settings', payload);
  return data;
}

async function testParser(config: ExternalParserConfig): Promise<TestResult> {
  const { data } = await apiClient.post<TestResult>('/organization/settings/parser/test', config);
  return data;
}

// ---------------------------------------------------------------------------
// Provider option cards
// ---------------------------------------------------------------------------

const PROVIDERS: {
  value: DocumentProcessingSettings['provider'];
  label: string;
  description: string;
  icon: React.ElementType;
  badge?: string;
}[] = [
  {
    value: 'docling',
    label: 'Standard',
    description: 'Structure-aware extraction using docling. Preserves tables and headings. Runs locally on CPU.',
    icon: FileText,
    badge: 'Default',
  },
  {
    value: 'legacy',
    label: 'Legacy',
    description: 'Fast flat-text extraction using PyMuPDF. No table structure. Best for simple text-heavy documents.',
    icon: Zap,
  },
  {
    value: 'external',
    label: 'External GPU Parser',
    description: 'Connect your own GPU-accelerated parser service. Supports OCR and compliance-aware chunking.',
    icon: Server,
    badge: 'Bring Your Own',
  },
];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function Settings() {
  const user = useAuthStore((s) => s.user);

  // Remote state
  const { data: remote, isLoading } = useQuery({
    queryKey: ['org-settings'],
    queryFn: fetchOrgSettings,
  });

  // Local form state
  const [provider, setProvider] = useState<DocumentProcessingSettings['provider']>('docling');
  const [extUrl, setExtUrl] = useState('');
  const [extKey, setExtKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [synced, setSynced] = useState(false);

  // Sync local state from remote once loaded
  if (remote && !synced) {
    const dp = remote.document_processing;
    setProvider(dp.provider);
    setExtUrl(dp.external_parser?.url ?? '');
    setExtKey(dp.external_parser?.api_key ?? '');
    setSynced(true);
  }

  const saveMutation = useMutation({
    mutationFn: (payload: Partial<OrgSettings>) => saveOrgSettings(payload),
  });

  const testMutation = useMutation({
    mutationFn: (config: ExternalParserConfig) => testParser(config),
    onSuccess: (result) => setTestResult(result),
    onError: (err) => setTestResult({ ok: false, error: getApiErrorMessage(err) }),
  });

  function handleSave() {
    const dp: DocumentProcessingSettings = {
      provider,
      external_parser:
        provider === 'external' && extUrl && extKey
          ? { url: extUrl, api_key: extKey }
          : null,
    };
    saveMutation.mutate({ document_processing: dp });
  }

  function handleTest() {
    setTestResult(null);
    testMutation.mutate({ url: extUrl, api_key: extKey });
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="max-w-3xl mx-auto space-y-8"
      >
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <SettingsIcon className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-white">Settings</h1>
            <p className="text-sm text-gray-400">{user?.organization_name ?? 'Organization'}</p>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center gap-2 text-gray-400 py-12 justify-center">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Loading settings...</span>
          </div>
        ) : (
          <>
            {/* Document Processing section */}
            <section className="rounded-xl border border-gray-800 bg-gray-900/60 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-800 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-semibold text-white">Document Processing</h2>
              </div>

              <div className="p-6 space-y-4">
                <p className="text-sm text-gray-400">
                  Choose how uploaded documents are parsed. This setting applies to all new
                  uploads for your organization.
                </p>

                {/* Provider cards */}
                <div className="space-y-3">
                  {PROVIDERS.map(({ value, label, description, icon: Icon, badge }) => (
                    <button
                      key={value}
                      onClick={() => {
                        setProvider(value);
                        setTestResult(null);
                      }}
                      className={cn(
                        'w-full text-left rounded-lg border p-4 transition-colors',
                        provider === value
                          ? 'border-indigo-500 bg-indigo-500/10'
                          : 'border-gray-700 bg-gray-800/40 hover:border-gray-600'
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={cn(
                            'mt-0.5 p-1.5 rounded-md',
                            provider === value
                              ? 'bg-indigo-500/20 text-indigo-400'
                              : 'bg-gray-700 text-gray-400'
                          )}
                        >
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-white">{label}</span>
                            {badge && (
                              <span className="text-xs px-1.5 py-0.5 rounded bg-gray-700 text-gray-300">
                                {badge}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-400 mt-0.5">{description}</p>
                        </div>
                        <div
                          className={cn(
                            'w-4 h-4 mt-0.5 rounded-full border-2 flex-shrink-0',
                            provider === value
                              ? 'border-indigo-400 bg-indigo-400'
                              : 'border-gray-600'
                          )}
                        />
                      </div>
                    </button>
                  ))}
                </div>

                {/* External parser config fields */}
                {provider === 'external' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-4 pt-2"
                  >
                    <div className="rounded-lg border border-gray-700 bg-gray-800/60 p-4 space-y-4">
                      <div className="space-y-1.5">
                        <Label htmlFor="ext-url" className="text-xs text-gray-300">
                          Parser URL
                        </Label>
                        <Input
                          id="ext-url"
                          value={extUrl}
                          onChange={(e) => {
                            setExtUrl(e.target.value);
                            setTestResult(null);
                          }}
                          placeholder="https://your-parser-service.example.com"
                          className="bg-gray-900 border-gray-700 text-sm"
                        />
                        <p className="text-xs text-gray-500">
                          Base URL of your parser service. Must implement the VendorAuditAI
                          Parser Contract — see{' '}
                          <code className="text-gray-400">parser-service/PARSER_CONTRACT.md</code>.
                        </p>
                      </div>

                      <div className="space-y-1.5">
                        <Label htmlFor="ext-key" className="text-xs text-gray-300">
                          API Key
                        </Label>
                        <div className="relative">
                          <Input
                            id="ext-key"
                            type={showKey ? 'text' : 'password'}
                            value={extKey}
                            onChange={(e) => {
                              setExtKey(e.target.value);
                              setTestResult(null);
                            }}
                            placeholder="Bearer token for /parse endpoint"
                            className="bg-gray-900 border-gray-700 text-sm pr-10"
                          />
                          <button
                            type="button"
                            onClick={() => setShowKey((v) => !v)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                            tabIndex={-1}
                          >
                            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                      </div>

                      {/* Test connection */}
                      <div className="flex items-center gap-3">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleTest}
                          disabled={!extUrl || !extKey || testMutation.isPending}
                          className="text-xs border-gray-600"
                        >
                          {testMutation.isPending ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                          ) : null}
                          Test Connection
                        </Button>

                        {testResult && (
                          <div className="flex items-center gap-1.5 text-xs">
                            {testResult.ok ? (
                              <>
                                <CheckCircle className="w-4 h-4 text-green-400" />
                                <span className="text-green-400">Connected</span>
                              </>
                            ) : (
                              <>
                                <XCircle className="w-4 h-4 text-red-400" />
                                <span className="text-red-400">
                                  {testResult.error ?? 'Connection failed'}
                                </span>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </div>
            </section>

            {/* Save + status */}
            <div className="flex items-center gap-4">
              <Button
                onClick={handleSave}
                disabled={saveMutation.isPending}
                className="bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                {saveMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                Save Changes
              </Button>

              {saveMutation.isSuccess && (
                <motion.div
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-center gap-1.5 text-sm text-green-400"
                >
                  <CheckCircle className="w-4 h-4" />
                  Saved
                </motion.div>
              )}

              {saveMutation.isError && (
                <span className="text-sm text-red-400">
                  {getApiErrorMessage(saveMutation.error)}
                </span>
              )}
            </div>
          </>
        )}
      </motion.div>
    </div>
  );
}
