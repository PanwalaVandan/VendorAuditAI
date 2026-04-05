import { AlertTriangle, AlertCircle, AlertOctagon, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import type { Severity } from '@/types/api';

interface FindingsSummaryProps {
  bySeverity: Record<Severity, number>;
  total: number;
}

interface SeverityStatConfig {
  severity: Severity;
  label: string;
  icon: typeof AlertOctagon;
  bgColor: string;
  textColor: string;
  iconColor: string;
}

const severityConfigs: SeverityStatConfig[] = [
  {
    severity: 'critical',
    label: 'Critical',
    icon: AlertOctagon,
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    iconColor: 'text-red-500',
  },
  {
    severity: 'high',
    label: 'High',
    icon: AlertTriangle,
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-700',
    iconColor: 'text-orange-500',
  },
  {
    severity: 'medium',
    label: 'Medium',
    icon: AlertCircle,
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    iconColor: 'text-yellow-500',
  },
  {
    severity: 'low',
    label: 'Low',
    icon: Info,
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    iconColor: 'text-blue-500',
  },
  {
    severity: 'info',
    label: 'Info',
    icon: Info,
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-700',
    iconColor: 'text-gray-500',
  },
];

/**
 * FindingsSummary - Displays summary statistics of findings by severity.
 * Shows a grid of cards with counts for each severity level.
 */
export function FindingsSummary({ bySeverity, total }: FindingsSummaryProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          Analysis Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {severityConfigs.map((config) => {
            const count = bySeverity[config.severity] || 0;
            const Icon = config.icon;

            return (
              <div
                key={config.severity}
                className={`${config.bgColor} rounded-lg p-4 flex items-center gap-3`}
              >
                <div className={`${config.iconColor}`}>
                  <Icon className="h-8 w-8" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${config.textColor}`}>{count}</p>
                  <p className="text-sm text-muted-foreground">{config.label}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Total findings bar */}
        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Total Findings</span>
            <span className="text-sm font-bold">{total}</span>
          </div>
          {total > 0 && (
            <div className="h-3 bg-secondary rounded-full overflow-hidden flex">
              {severityConfigs.map((config) => {
                const count = bySeverity[config.severity] || 0;
                const percentage = (count / total) * 100;
                if (percentage === 0) return null;

                const colorMap: Record<Severity, string> = {
                  critical: 'bg-red-500',
                  high: 'bg-orange-500',
                  medium: 'bg-yellow-500',
                  low: 'bg-blue-500',
                  info: 'bg-gray-500',
                };

                return (
                  <div
                    key={config.severity}
                    className={`${colorMap[config.severity]} h-full`}
                    style={{ width: `${percentage}%` }}
                    title={`${config.label}: ${count} (${percentage.toFixed(1)}%)`}
                  />
                );
              })}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
