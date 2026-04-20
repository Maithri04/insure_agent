import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import AgentStepsPanel from "../components/AgentStepsPanel";
import Button from "../components/Button";
import Card from "../components/Card";
import InputField from "../components/InputField";
import MissingEvidencePanel from "../components/MissingEvidencePanel";
import SectionTitle from "../components/SectionTitle";
import SelectField from "../components/SelectField";
import TextArea from "../components/TextArea";
import { useAppState } from "../context/AppStateContext";
import { runAgent } from "../services/api";

const STEP_LABELS = [
  "Understanding patient",
  "Validating data",
  "Fixing issues",
  "Improving justification",
  "Analyzing risk",
  "Predicting approval",
];

const RUN_TOTAL_MS = 10_000;

export default function AgentForm() {
  const navigate = useNavigate();
  const { soapData, patientMeta, setAgentResult, setCaseId } = useAppState();
  const [showRightPanel, setShowRightPanel] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(-1);
  const stepTimerRef = useRef(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    patient_name: patientMeta?.patient_name || "",
    age: patientMeta?.patient_age || "",
    gender: patientMeta?.patient_gender || "",
    disease: soapData?.assessment || patientMeta?.description || "",
    medications: patientMeta?.medications || "",
    tpa: "",
    procedure: "",
    duration: "",
    prior_treatment: "",
    severity: "",
    investigations: "",
    referral: "",
  });

  const evidence = useMemo(
    () => ({
      duration: Boolean(form.duration.trim()),
      treatment: Boolean(form.prior_treatment.trim()),
      severity: Boolean(form.severity.trim()),
      investigations: Boolean(form.investigations.trim()),
      referral: Boolean(form.referral.trim()),
    }),
    [form],
  );

  const stepState = useMemo(
    () =>
      STEP_LABELS.map((name, index) => ({
        name,
        status: !showRightPanel
          ? "pending"
          : index < activeStepIndex
            ? "done"
            : index === activeStepIndex
              ? "loading"
              : "pending",
      })),
    [showRightPanel, activeStepIndex],
  );

  const onChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const buildPayload = () => ({
    patient_name: form.patient_name,
    patient_age: Number(form.age),
    patient_gender: String(form.gender || "").toLowerCase(),
    tpa: form.tpa,
    disease_description: form.disease,
    medications: form.medications,
    procedure: form.procedure,
    duration_of_symptoms: form.duration || null,
    prior_treatment: form.prior_treatment || null,
    severity: form.severity || null,
    investigations: form.investigations || null,
    specialist_referral: form.referral || null,
  });

  const startStepAnimation = () => {
    if (stepTimerRef.current) {
      clearInterval(stepTimerRef.current);
      stepTimerRef.current = null;
    }
    setActiveStepIndex(0);
    const stepMs = Math.max(800, Math.floor(RUN_TOTAL_MS / STEP_LABELS.length));
    stepTimerRef.current = setInterval(() => {
      setActiveStepIndex((prev) => {
        const next = prev + 1;
        if (next >= STEP_LABELS.length) {
          clearInterval(stepTimerRef.current);
          stepTimerRef.current = null;
          return STEP_LABELS.length; // all done
        }
        return next;
      });
    }, stepMs);
  };

  const stopStepAnimation = () => {
    if (stepTimerRef.current) {
      clearInterval(stepTimerRef.current);
      stepTimerRef.current = null;
    }
    setActiveStepIndex(-1);
  };

  const runAgentWith10sUX = async () => {
    setError("");
    setShowRightPanel(true);
    setSubmitting(true);
    startStepAnimation();

    const payload = buildPayload();
    const apiPromise = runAgent(payload);
    const timerPromise = new Promise((resolve) => setTimeout(resolve, RUN_TOTAL_MS));

    try {
      const [, result] = await Promise.all([timerPromise, apiPromise]);
      setAgentResult(result);
      setCaseId(result.case_id || result.request_id || "");
      navigate("/agent-result");
    } catch (apiError) {
      setError(apiError.message);
      stopStepAnimation();
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = () => {
    if (!form.patient_name || !form.age || !form.gender || !form.disease || !form.tpa) {
      setError("Please fill all mandatory fields before verification.");
      return;
    }
    runAgentWith10sUX();
  };

  const handleSubmit = async () => {
    // Submit behaves same as Verify (single endpoint); kept for workflow clarity.
    if (!form.patient_name || !form.age || !form.gender || !form.disease || !form.tpa) {
      setError("Please fill all mandatory fields before submission.");
      return;
    }
    await runAgentWith10sUX();
  };

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Agent Run"
        description="Fill patient, treatment and justification details for insurance approval prediction."
      />
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-2 space-y-4">
          <Card className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <InputField label="Patient Name" name="patient_name" value={form.patient_name} onChange={onChange} />
              <InputField label="Age" name="age" type="number" value={form.age} onChange={onChange} />
              <SelectField
                label="Gender"
                name="gender"
                value={form.gender}
                onChange={onChange}
                options={[
                  { label: "Male", value: "male" },
                  { label: "Female", value: "female" },
                  { label: "Other", value: "other" },
                ]}
              />
            </div>
            <TextArea label="Disease" name="disease" value={form.disease} onChange={onChange} rows={4} />
            <TextArea label="Medications" name="medications" value={form.medications} onChange={onChange} rows={3} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InputField label="TPA / Insurer" name="tpa" value={form.tpa} onChange={onChange} placeholder="e.g. Demo TPA" />
              <InputField label="Procedure" name="procedure" value={form.procedure} onChange={onChange} />
            </div>
          </Card>
          <Card>
            <SectionTitle title="Structured Clinical Justification" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InputField label="Duration" name="duration" value={form.duration} onChange={onChange} />
              <InputField label="Prior Treatment" name="prior_treatment" value={form.prior_treatment} onChange={onChange} />
              <InputField label="Severity" name="severity" value={form.severity} onChange={onChange} />
              <InputField label="Investigations" name="investigations" value={form.investigations} onChange={onChange} />
              <InputField label="Referral" name="referral" value={form.referral} onChange={onChange} />
            </div>
          </Card>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={handleVerify} disabled={submitting}>Verify</Button>
            <Button onClick={handleSubmit} loading={submitting} disabled={submitting}>Submit</Button>
          </div>
          {submitting && activeStepIndex >= STEP_LABELS.length && (
            <p className="text-xs text-gray-500">
              Finalizing response from AI… (this should complete within ~10 seconds; if your server is busy it may take a bit longer)
            </p>
          )}
        </div>
        <div className={`space-y-4 ${showRightPanel ? "block" : "hidden xl:block"}`}>
          <AgentStepsPanel steps={stepState} />
          <MissingEvidencePanel evidence={evidence} />
        </div>
      </div>
    </div>
  );
}
