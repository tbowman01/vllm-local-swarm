{{/*
Expand the name of the chart.
*/}}
{{- define "vllm-local-swarm.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "vllm-local-swarm.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "vllm-local-swarm.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "vllm-local-swarm.labels" -}}
helm.sh/chart: {{ include "vllm-local-swarm.chart" . }}
{{ include "vllm-local-swarm.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "vllm-local-swarm.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vllm-local-swarm.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "vllm-local-swarm.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "vllm-local-swarm.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
vLLM Phi labels
*/}}
{{- define "vllm-local-swarm.vllm-phi.labels" -}}
{{ include "vllm-local-swarm.labels" . }}
app.kubernetes.io/component: vllm-phi
{{- end }}

{{/*
vLLM Phi selector labels
*/}}
{{- define "vllm-local-swarm.vllm-phi.selectorLabels" -}}
{{ include "vllm-local-swarm.selectorLabels" . }}
app.kubernetes.io/component: vllm-phi
{{- end }}

{{/*
Ray Head labels
*/}}
{{- define "vllm-local-swarm.ray-head.labels" -}}
{{ include "vllm-local-swarm.labels" . }}
app.kubernetes.io/component: ray-head
{{- end }}

{{/*
Ray Head selector labels
*/}}
{{- define "vllm-local-swarm.ray-head.selectorLabels" -}}
{{ include "vllm-local-swarm.selectorLabels" . }}
app.kubernetes.io/component: ray-head
{{- end }}

{{/*
Ray Worker labels
*/}}
{{- define "vllm-local-swarm.ray-worker.labels" -}}
{{ include "vllm-local-swarm.labels" . }}
app.kubernetes.io/component: ray-worker
{{- end }}

{{/*
Ray Worker selector labels
*/}}
{{- define "vllm-local-swarm.ray-worker.selectorLabels" -}}
{{ include "vllm-local-swarm.selectorLabels" . }}
app.kubernetes.io/component: ray-worker
{{- end }}

{{/*
Langfuse Web labels
*/}}
{{- define "vllm-local-swarm.langfuse-web.labels" -}}
{{ include "vllm-local-swarm.labels" . }}
app.kubernetes.io/component: langfuse-web
{{- end }}

{{/*
Langfuse Web selector labels
*/}}
{{- define "vllm-local-swarm.langfuse-web.selectorLabels" -}}
{{ include "vllm-local-swarm.selectorLabels" . }}
app.kubernetes.io/component: langfuse-web
{{- end }}

{{/*
ClickHouse labels
*/}}
{{- define "vllm-local-swarm.clickhouse.labels" -}}
{{ include "vllm-local-swarm.labels" . }}
app.kubernetes.io/component: clickhouse
{{- end }}

{{/*
ClickHouse selector labels
*/}}
{{- define "vllm-local-swarm.clickhouse.selectorLabels" -}}
{{ include "vllm-local-swarm.selectorLabels" . }}
app.kubernetes.io/component: clickhouse
{{- end }}

{{/*
Qdrant labels
*/}}
{{- define "vllm-local-swarm.qdrant.labels" -}}
{{ include "vllm-local-swarm.labels" . }}
app.kubernetes.io/component: qdrant
{{- end }}

{{/*
Qdrant selector labels
*/}}
{{- define "vllm-local-swarm.qdrant.selectorLabels" -}}
{{ include "vllm-local-swarm.selectorLabels" . }}
app.kubernetes.io/component: qdrant
{{- end }}

{{/*
Image registry
*/}}
{{- define "vllm-local-swarm.imageRegistry" -}}
{{- if .Values.global.imageRegistry }}
{{- printf "%s/" .Values.global.imageRegistry }}
{{- end }}
{{- end }}

{{/*
Storage class
*/}}
{{- define "vllm-local-swarm.storageClass" -}}
{{- if .Values.global.storageClass }}
{{- .Values.global.storageClass }}
{{- else if .storageClass }}
{{- .storageClass }}
{{- end }}
{{- end }}