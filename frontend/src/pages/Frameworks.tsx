import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Layers, Trash2, Pencil, Play, X, ChevronDown, ChevronUp, Copy, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from '@/components/ui';
import apiClient, { getApiErrorMessage } from '@/lib/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface CustomControl {
  id: string;
  framework_id: string;
  control_id: string;
  name: string;
  description: string;
  category: string | null;
  guidance: string | null;
  order_index: number;
  created_at: string;
  updated_at: string;
}

interface CustomFramework {
  id: string;
  organization_id: string;
  created_by: string;
  name: string;
  version: string;
  description: string | null;
  is_active: boolean;
  controls: CustomControl[];
  created_at: string;
  updated_at: string;
}

interface FrameworkSummary {
  id: string;
  name: string;
  version: string;
  description: string | null;
  is_active: boolean;
  control_count: number;
  created_at: string;
  updated_at: string;
}

// Types for built-in framework API responses
interface BuiltinFrameworkSummary {
  id: string;
  name: string;
  version: string;
  description: string;
  category_count: number;
  control_count: number;
}

interface BuiltinControlRequirement {
  id: string;
  description: string;
  guidance?: string;
}

interface BuiltinControl {
  id: string;
  name: string;
  description: string;
  category: string;
  framework_id: string;
  requirements: BuiltinControlRequirement[];
}

// ── Empty blank control for the add-control form ─────────────────────────────
const BLANK_CONTROL = { control_id: '', name: '', description: '', category: '', guidance: '', order_index: 0 };

// ── Animation variants ───────────────────────────────────────────────────────
const container = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const item = { hidden: { y: 16, opacity: 0 }, visible: { y: 0, opacity: 1, transition: { type: 'spring' as const, stiffness: 100 } } };

// ── Component ────────────────────────────────────────────────────────────────

export function Frameworks() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Which framework is open for editing (null = list view)
  const [editingId, setEditingId] = useState<string | null>(null);
  // Show create form
  const [showCreate, setShowCreate] = useState(false);
  // Create form state
  const [createForm, setCreateForm] = useState({ name: '', version: '1.0', description: '' });
  const [createError, setCreateError] = useState<string | null>(null);
  // Clone modal
  const [showClone, setShowClone] = useState(false);
  const [cloneStep, setCloneStep] = useState<'framework' | 'controls'>('framework');
  const [cloneTarget, setCloneTarget] = useState<string>('');
  const [cloneSearch, setCloneSearch] = useState('');
  const [cloneSelected, setCloneSelected] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);
  // Control form
  const [controlForm, setControlForm] = useState({ ...BLANK_CONTROL });
  const [editingControlId, setEditingControlId] = useState<string | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);
  const [expandedControls, setExpandedControls] = useState(true);

  // ── Queries ────────────────────────────────────────────────────────────────

  const { data: listData, isLoading } = useQuery({
    queryKey: ['custom-frameworks'],
    queryFn: async () => {
      const res = await apiClient.get('/custom-frameworks');
      return res.data;
    },
  });

  const { data: detailData } = useQuery({
    queryKey: ['custom-framework', editingId],
    queryFn: async () => {
      const res = await apiClient.get(`/custom-frameworks/${editingId}`);
      return res.data as CustomFramework;
    },
    enabled: !!editingId,
  });

  const { data: builtinFrameworks, isLoading: builtinLoading } = useQuery({
    queryKey: ['builtin-frameworks'],
    queryFn: async () => {
      const res = await apiClient.get('/frameworks');
      return res.data.frameworks as BuiltinFrameworkSummary[];
    },
    enabled: showClone,
    staleTime: Infinity,
  });

  const { data: builtinControls, isLoading: controlsLoading } = useQuery({
    queryKey: ['builtin-controls', cloneTarget],
    queryFn: async () => {
      const res = await apiClient.get(`/frameworks/${cloneTarget}/controls`);
      return res.data as BuiltinControl[];
    },
    enabled: showClone && cloneStep === 'controls' && !!cloneTarget,
    staleTime: Infinity,
  });

  const frameworks: FrameworkSummary[] = listData?.data || [];
  const detail: CustomFramework | undefined = detailData;

  // ── Mutations ──────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: async (payload: typeof createForm) => {
      const res = await apiClient.post('/custom-frameworks', payload);
      return res.data as CustomFramework;
    },
    onSuccess: (fw) => {
      queryClient.invalidateQueries({ queryKey: ['custom-frameworks'] });
      setShowCreate(false);
      setCreateForm({ name: '', version: '1.0', description: '' });
      setEditingId(fw.id);
    },
    onError: (e) => setCreateError(getApiErrorMessage(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/custom-frameworks/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-frameworks'] });
      if (editingId) setEditingId(null);
    },
  });

  const updateFrameworkMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<CustomFramework> }) => {
      const res = await apiClient.patch(`/custom-frameworks/${id}`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-frameworks'] });
      queryClient.invalidateQueries({ queryKey: ['custom-framework', editingId] });
    },
  });

  const addControlMutation = useMutation({
    mutationFn: async (payload: typeof controlForm) => {
      const res = await apiClient.post(`/custom-frameworks/${editingId}/controls`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-framework', editingId] });
      setControlForm({ ...BLANK_CONTROL });
      setControlError(null);
    },
    onError: (e) => setControlError(getApiErrorMessage(e)),
  });

  const updateControlMutation = useMutation({
    mutationFn: async ({ controlId, payload }: { controlId: string; payload: Partial<typeof controlForm> }) => {
      const res = await apiClient.patch(`/custom-frameworks/${editingId}/controls/${controlId}`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['custom-framework', editingId] });
      setEditingControlId(null);
      setControlForm({ ...BLANK_CONTROL });
      setControlError(null);
    },
    onError: (e) => setControlError(getApiErrorMessage(e)),
  });

  const deleteControlMutation = useMutation({
    mutationFn: async (controlId: string) => {
      await apiClient.delete(`/custom-frameworks/${editingId}/controls/${controlId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['custom-framework', editingId] }),
  });

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleCloneClose = () => {
    setShowClone(false);
    setCloneStep('framework');
    setCloneTarget('');
    setCloneSearch('');
    setCloneSelected(new Set());
  };

  const handleCloneImport = async () => {
    if (!builtinControls || cloneSelected.size === 0) return;
    setImporting(true);
    const toImport = builtinControls.filter(c => cloneSelected.has(c.id));
    const existingCount = detail?.controls.length ?? 0;
    try {
      for (let i = 0; i < toImport.length; i++) {
        const ctrl = toImport[i];
        await apiClient.post(`/custom-frameworks/${editingId}/controls`, {
          control_id: ctrl.id,
          name: ctrl.name,
          description: ctrl.description,
          category: ctrl.category,
          guidance: ctrl.requirements?.map(r => r.description).join(' | ').slice(0, 500) || '',
          order_index: existingCount + i,
        });
      }
      queryClient.invalidateQueries({ queryKey: ['custom-framework', editingId] });
      handleCloneClose();
    } finally {
      setImporting(false);
    }
  };

  const handleControlSubmit = () => {
    if (!controlForm.control_id.trim() || !controlForm.name.trim() || !controlForm.description.trim()) {
      setControlError('Control ID, Name, and Description are required.');
      return;
    }
    if (editingControlId) {
      updateControlMutation.mutate({ controlId: editingControlId, payload: controlForm });
    } else {
      addControlMutation.mutate(controlForm);
    }
  };

  const startEditControl = (ctrl: CustomControl) => {
    setEditingControlId(ctrl.id);
    setControlForm({
      control_id: ctrl.control_id,
      name: ctrl.name,
      description: ctrl.description,
      category: ctrl.category || '',
      guidance: ctrl.guidance || '',
      order_index: ctrl.order_index,
    });
    setControlError(null);
  };

  const cancelControlEdit = () => {
    setEditingControlId(null);
    setControlForm({ ...BLANK_CONTROL });
    setControlError(null);
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  // Detail / edit view
  if (editingId && detail) {
    return (
      <motion.div className="p-8" initial="hidden" animate="visible" variants={container}>
        {/* Header */}
        <motion.div variants={item} className="mb-6 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setEditingId(null)}>← Back</Button>
          <div>
            <h1 className="text-2xl font-bold neon-text">
              EDIT <span className="text-primary">FRAMEWORK</span>
            </h1>
            <p className="text-muted-foreground text-sm">{detail.name} · v{detail.version} · {detail.controls.length} controls</p>
          </div>
          <div className="ml-auto flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/analysis?custom_framework_id=${detail.id}`)}
            >
              <Play className="h-4 w-4 mr-1" />
              Run Analysis
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-destructive border-destructive/40 hover:bg-destructive/10"
              onClick={() => deleteMutation.mutate(detail.id)}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Delete Framework
            </Button>
          </div>
        </motion.div>

        {/* Framework details */}
        <motion.div variants={item}>
          <Card className="glass-panel-liquid mb-6">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Pencil className="h-4 w-4" /> Framework Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <FrameworkDetailForm
                framework={detail}
                onSave={(payload) => updateFrameworkMutation.mutate({ id: detail.id, payload })}
                isSaving={updateFrameworkMutation.isPending}
              />
            </CardContent>
          </Card>
        </motion.div>

        {/* Controls */}
        <motion.div variants={item}>
          <Card className="glass-panel-liquid">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Layers className="h-4 w-4" />
                  Controls ({detail.controls.length})
                  <button
                    onClick={() => setExpandedControls(!expandedControls)}
                    className="ml-1 text-muted-foreground hover:text-foreground"
                  >
                    {expandedControls ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                </CardTitle>
                <Button variant="outline" size="sm" onClick={() => setShowClone(true)}>
                  <Copy className="h-4 w-4 mr-1" />
                  Clone from Built-in
                </Button>
              </div>
            </CardHeader>

            <AnimatePresence>
              {expandedControls && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <CardContent>
                    {/* Controls table */}
                    {detail.controls.length > 0 && (
                      <div className="overflow-x-auto rounded-lg border border-border mb-6">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/30">
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">ID</th>
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">Name</th>
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">Category</th>
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">Description</th>
                              <th className="text-left px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detail.controls.map((ctrl) => (
                              <tr key={ctrl.id} className="border-b border-border/50 hover:bg-muted/10">
                                <td className="px-4 py-3 font-mono text-primary text-xs">{ctrl.control_id}</td>
                                <td className="px-4 py-3 font-medium">{ctrl.name}</td>
                                <td className="px-4 py-3">
                                  {ctrl.category && (
                                    <span className="text-xs bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-full">
                                      {ctrl.category}
                                    </span>
                                  )}
                                </td>
                                <td className="px-4 py-3 text-muted-foreground text-xs max-w-xs truncate">{ctrl.description}</td>
                                <td className="px-4 py-3">
                                  <div className="flex gap-2">
                                    <Button variant="ghost" size="sm" onClick={() => startEditControl(ctrl)}>
                                      <Pencil className="h-3.5 w-3.5" />
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="text-destructive hover:text-destructive"
                                      onClick={() => deleteControlMutation.mutate(ctrl.id)}
                                      disabled={deleteControlMutation.isPending}
                                    >
                                      <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Add / edit control form */}
                    <div className="border border-border rounded-lg p-4 bg-muted/10">
                      <h4 className="text-sm font-semibold mb-3">
                        {editingControlId ? 'Edit Control' : 'Add Control'}
                      </h4>
                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <div>
                          <label className="block text-xs text-muted-foreground mb-1">Control ID *</label>
                          <Input
                            placeholder="e.g. CC-1"
                            value={controlForm.control_id}
                            onChange={(e) => setControlForm({ ...controlForm, control_id: e.target.value })}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-muted-foreground mb-1">Category</label>
                          <Input
                            placeholder="e.g. Security"
                            value={controlForm.category}
                            onChange={(e) => setControlForm({ ...controlForm, category: e.target.value })}
                          />
                        </div>
                      </div>
                      <div className="mb-3">
                        <label className="block text-xs text-muted-foreground mb-1">Name *</label>
                        <Input
                          placeholder="Control name"
                          value={controlForm.name}
                          onChange={(e) => setControlForm({ ...controlForm, name: e.target.value })}
                        />
                      </div>
                      <div className="mb-3">
                        <label className="block text-xs text-muted-foreground mb-1">Description *</label>
                        <textarea
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                          rows={3}
                          placeholder="What must be true for this control to pass? The AI uses this to find gaps."
                          value={controlForm.description}
                          onChange={(e) => setControlForm({ ...controlForm, description: e.target.value })}
                        />
                      </div>
                      <div className="mb-3">
                        <label className="block text-xs text-muted-foreground mb-1">Guidance (optional — hints for the AI)</label>
                        <Input
                          placeholder="e.g. Look for: encryption policy, key management, HSM documentation"
                          value={controlForm.guidance}
                          onChange={(e) => setControlForm({ ...controlForm, guidance: e.target.value })}
                        />
                      </div>
                      {controlError && (
                        <p className="text-destructive text-sm mb-3">{controlError}</p>
                      )}
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={handleControlSubmit}
                          disabled={addControlMutation.isPending || updateControlMutation.isPending}
                        >
                          {editingControlId ? 'Update Control' : 'Add Control'}
                        </Button>
                        {editingControlId && (
                          <Button variant="ghost" size="sm" onClick={cancelControlEdit}>Cancel</Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </motion.div>
              )}
            </AnimatePresence>
          </Card>
        </motion.div>

        {/* Clone from built-in modal */}
        <AnimatePresence>
          {showClone && (
            <motion.div
              className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div
                className="bg-background border border-border rounded-2xl w-[640px] max-h-[80vh] flex flex-col shadow-2xl"
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
              >
                {/* Modal header */}
                <div className="p-5 border-b border-border flex items-center justify-between flex-shrink-0">
                  <div>
                    <h2 className="text-base font-semibold">Clone from Built-in Framework</h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {cloneStep === 'framework'
                        ? 'Step 1 of 2 — Pick a framework'
                        : `Step 2 of 2 — Select controls to import (${cloneSelected.size} selected)`}
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={handleCloneClose}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {/* Step 1 — Framework picker */}
                {cloneStep === 'framework' && (
                  <div className="flex-1 overflow-y-auto p-5">
                    {builtinLoading ? (
                      <div className="space-y-2">
                        {[1,2,3,4].map(i => (
                          <div key={i} className="h-12 bg-muted/40 rounded-lg animate-pulse" />
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {(builtinFrameworks ?? []).map(fw => (
                          <button
                            key={fw.id}
                            onClick={() => setCloneTarget(fw.id)}
                            className={`w-full flex items-center justify-between p-3 rounded-lg border text-sm transition-colors ${
                              cloneTarget === fw.id
                                ? 'border-primary bg-primary/10 text-primary'
                                : 'border-border hover:border-muted-foreground'
                            }`}
                          >
                            <div className="text-left">
                              <span className="font-medium block">{fw.name}</span>
                              {fw.description && (
                                <span className="text-xs text-muted-foreground line-clamp-1">{fw.description}</span>
                              )}
                            </div>
                            <span className="text-xs text-muted-foreground ml-4 flex-shrink-0">
                              {fw.control_count} controls
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Step 2 — Controls picker */}
                {cloneStep === 'controls' && (() => {
                  const filteredControls = (builtinControls ?? []).filter(ctrl => {
                    if (!cloneSearch.trim()) return true;
                    const q = cloneSearch.toLowerCase();
                    return (
                      ctrl.id.toLowerCase().includes(q) ||
                      ctrl.name.toLowerCase().includes(q) ||
                      ctrl.category.toLowerCase().includes(q) ||
                      ctrl.description.toLowerCase().includes(q)
                    );
                  });
                  const allFilteredSelected = filteredControls.length > 0 && filteredControls.every(c => cloneSelected.has(c.id));

                  return (
                    <>
                      <div className="p-4 border-b border-border flex-shrink-0 space-y-3">
                        {/* Search */}
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            className="pl-9 h-9 text-sm"
                            placeholder="Search by ID, name, category or description..."
                            value={cloneSearch}
                            onChange={e => setCloneSearch(e.target.value)}
                          />
                        </div>
                        {/* Select all / clear */}
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{filteredControls.length} of {builtinControls?.length ?? 0} controls shown</span>
                          <div className="flex gap-3">
                            <button
                              className="text-primary hover:underline"
                              onClick={() => {
                                const next = new Set(cloneSelected);
                                filteredControls.forEach(c => next.add(c.id));
                                setCloneSelected(next);
                              }}
                            >
                              Select all shown
                            </button>
                            <button
                              className="hover:underline"
                              onClick={() => {
                                const next = new Set(cloneSelected);
                                filteredControls.forEach(c => next.delete(c.id));
                                setCloneSelected(next);
                              }}
                            >
                              Clear shown
                            </button>
                          </div>
                        </div>
                      </div>

                      <div className="flex-1 overflow-y-auto">
                        {controlsLoading ? (
                          <div className="p-4 space-y-2">
                            {[1,2,3,4,5].map(i => (
                              <div key={i} className="h-10 bg-muted/40 rounded animate-pulse" />
                            ))}
                          </div>
                        ) : filteredControls.length === 0 ? (
                          <p className="p-6 text-center text-sm text-muted-foreground">No controls match your search.</p>
                        ) : (
                          <div className="divide-y divide-border/50">
                            {filteredControls.map(ctrl => (
                              <label
                                key={ctrl.id}
                                className={`flex items-start gap-3 px-5 py-3 cursor-pointer hover:bg-muted/10 transition-colors ${
                                  cloneSelected.has(ctrl.id) ? 'bg-primary/5' : ''
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  className="mt-0.5 accent-primary flex-shrink-0"
                                  checked={cloneSelected.has(ctrl.id)}
                                  onChange={e => {
                                    const next = new Set(cloneSelected);
                                    e.target.checked ? next.add(ctrl.id) : next.delete(ctrl.id);
                                    setCloneSelected(next);
                                  }}
                                />
                                <div className="min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="font-mono text-xs text-primary">{ctrl.id}</span>
                                    {ctrl.category && (
                                      <span className="text-xs bg-muted/60 px-1.5 py-0.5 rounded text-muted-foreground">{ctrl.category}</span>
                                    )}
                                  </div>
                                  <p className="text-sm font-medium truncate">{ctrl.name}</p>
                                  <p className="text-xs text-muted-foreground line-clamp-1">{ctrl.description}</p>
                                </div>
                              </label>
                            ))}
                          </div>
                        )}
                      </div>
                    </>
                  );
                })()}

                {/* Footer */}
                <div className="p-4 border-t border-border flex justify-between gap-2 flex-shrink-0">
                  {cloneStep === 'framework' ? (
                    <>
                      <Button variant="ghost" size="sm" onClick={handleCloneClose}>Cancel</Button>
                      <Button
                        size="sm"
                        disabled={!cloneTarget}
                        onClick={() => {
                          setCloneStep('controls');
                          setCloneSearch('');
                          setCloneSelected(new Set());
                        }}
                      >
                        Next: Select Controls
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button variant="ghost" size="sm" onClick={() => setCloneStep('framework')}>
                        Back
                      </Button>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={handleCloneClose}>Cancel</Button>
                        <Button
                          size="sm"
                          disabled={cloneSelected.size === 0 || importing}
                          onClick={handleCloneImport}
                        >
                          {importing ? `Importing...` : `Import ${cloneSelected.size} Control${cloneSelected.size !== 1 ? 's' : ''}`}
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  }

  // ── List view ────────────────────────────────────────────────────────────────
  return (
    <motion.div className="p-8" initial="hidden" animate="visible" variants={container}>
      {/* Header */}
      <motion.div variants={item} className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold neon-text flex items-center gap-3">
            CUSTOM <span className="text-primary">FRAMEWORKS</span>
            <motion.div
              className="w-2 h-2 rounded-full bg-primary"
              animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </h1>
          <p className="text-muted-foreground mt-1">Build and manage your own compliance frameworks for AI analysis</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Framework
        </Button>
      </motion.div>

      {/* Create form */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="mb-6"
          >
            <Card className="glass-panel-liquid border-primary/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center justify-between">
                  <span>Create Framework</span>
                  <Button variant="ghost" size="sm" onClick={() => { setShowCreate(false); setCreateError(null); }}>
                    <X className="h-4 w-4" />
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Name *</label>
                    <Input
                      placeholder="e.g. My Custom SOC2"
                      value={createForm.name}
                      onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Version</label>
                    <Input
                      placeholder="1.0"
                      value={createForm.version}
                      onChange={(e) => setCreateForm({ ...createForm, version: e.target.value })}
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <label className="block text-xs text-muted-foreground mb-1">Description</label>
                  <Input
                    placeholder="What is this framework for?"
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  />
                </div>
                {createError && <p className="text-destructive text-sm mb-3">{createError}</p>}
                <div className="flex gap-2">
                  <Button
                    onClick={() => {
                      setCreateError(null);
                      if (!createForm.name.trim()) { setCreateError('Name is required.'); return; }
                      createMutation.mutate(createForm);
                    }}
                    disabled={createMutation.isPending}
                  >
                    {createMutation.isPending ? 'Creating...' : 'Create & Edit'}
                  </Button>
                  <Button variant="ghost" onClick={() => { setShowCreate(false); setCreateError(null); }}>Cancel</Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="glass-panel-liquid animate-pulse">
              <CardContent className="p-6">
                <div className="h-5 bg-muted rounded w-3/4 mb-3" />
                <div className="h-3 bg-muted rounded w-1/2 mb-4" />
                <div className="h-3 bg-muted rounded w-full mb-2" />
                <div className="h-8 bg-muted rounded w-1/3 mt-4" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && frameworks.length === 0 && (
        <motion.div variants={item}>
          <Card className="glass-panel-liquid">
            <CardContent className="flex flex-col items-center justify-center py-20">
              <Layers className="h-16 w-16 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No custom frameworks yet</h3>
              <p className="text-muted-foreground text-center max-w-md mb-6">
                Build your own compliance framework and run AI analysis against your specific controls and requirements.
              </p>
              <Button onClick={() => setShowCreate(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Framework
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Framework cards */}
      {!isLoading && frameworks.length > 0 && (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          variants={container}
        >
          {frameworks.map((fw) => (
            <motion.div key={fw.id} variants={item}>
              <Card className="glass-panel-liquid hover:border-primary/30 transition-colors">
                <CardContent className="p-6">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                      <Layers className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold truncate">{fw.name}</h3>
                      <p className="text-xs text-muted-foreground">v{fw.version}</p>
                    </div>
                  </div>

                  <div className="flex gap-4 text-sm mb-3">
                    <span className="text-muted-foreground">
                      <strong className="text-foreground">{fw.control_count}</strong> controls
                    </span>
                    <span className="text-muted-foreground">
                      {new Date(fw.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {fw.description && (
                    <p className="text-xs text-muted-foreground mb-4 line-clamp-2">{fw.description}</p>
                  )}

                  <div className="flex gap-2 flex-wrap">
                    <Button variant="outline" size="sm" onClick={() => setEditingId(fw.id)}>
                      <Pencil className="h-3.5 w-3.5 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-destructive border-destructive/40 hover:bg-destructive/10"
                      onClick={() => deleteMutation.mutate(fw.id)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-3.5 w-3.5 mr-1" />
                      Delete
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => navigate(`/analysis?custom_framework_id=${fw.id}`)}
                    >
                      <Play className="h-3.5 w-3.5 mr-1" />
                      Analyze
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}

// ── Framework detail form subcomponent ───────────────────────────────────────

function FrameworkDetailForm({
  framework,
  onSave,
  isSaving,
}: {
  framework: CustomFramework;
  onSave: (payload: { name: string; version: string; description: string | null }) => void;
  isSaving: boolean;
}) {
  const [form, setForm] = useState({
    name: framework.name,
    version: framework.version,
    description: framework.description || '',
  });

  return (
    <div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Name *</label>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Version</label>
          <Input value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} />
        </div>
      </div>
      <div className="mb-4">
        <label className="block text-xs text-muted-foreground mb-1">Description</label>
        <Input
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </div>
      <Button
        size="sm"
        onClick={() => onSave({ ...form, description: form.description || null })}
        disabled={isSaving || !form.name.trim()}
      >
        {isSaving ? 'Saving...' : 'Save Details'}
      </Button>
    </div>
  );
}
