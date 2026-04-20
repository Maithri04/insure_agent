import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Card from "../components/Card";
import InputField from "../components/InputField";
import SectionTitle from "../components/SectionTitle";
import SelectField from "../components/SelectField";
import TextArea from "../components/TextArea";
import { useAppState } from "../context/AppStateContext";
import { generateSOAP } from "../services/api";

export default function SoapForm() {
  const navigate = useNavigate();
  const { setSoapData, setPatientMeta } = useAppState();
  const [form, setForm] = useState({
    patient_name: "",
    patient_age: "",
    patient_gender: "male",
    description: "",
    medications: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleGenerate = async () => {
    if (!form.patient_name || !form.patient_age || !form.patient_gender || !form.description) {
      setError("Patient name, age, gender and description are required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const soap = await generateSOAP({
        patient_name: form.patient_name,
        patient_age: Number(form.patient_age),
        patient_gender: form.patient_gender,
        raw_notes: form.description,
        medications: form.medications,
      });
      setSoapData(soap);
      setPatientMeta(form);
      navigate("/soap-report");
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <SectionTitle
        title="SOAP Generation"
        description="Create structured SOAP notes from patient clinical context."
      />
      <Card className="max-w-4xl">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <InputField label="Patient Name" name="patient_name" value={form.patient_name} onChange={onChange} />
          <InputField label="Age" name="patient_age" type="number" value={form.patient_age} onChange={onChange} />
          <SelectField
            label="Gender"
            name="patient_gender"
            value={form.patient_gender}
            onChange={onChange}
            options={[
              { label: "Male", value: "male" },
              { label: "Female", value: "female" },
              { label: "Other", value: "other" },
            ]}
          />
        </div>
        <div className="space-y-4">
          <TextArea
            label="Description"
            name="description"
            value={form.description}
            onChange={onChange}
            placeholder="Clinical complaints, exam, symptom history."
            rows={6}
          />
          <TextArea
            label="Medications"
            name="medications"
            value={form.medications}
            onChange={onChange}
            placeholder="Current or recent medications."
            rows={3}
          />
        </div>
        {error ? <p className="text-sm text-red-600 mt-4">{error}</p> : null}
        <div className="mt-4">
          <Button onClick={handleGenerate} loading={loading} disabled={loading}>
            Generate SOAP
          </Button>
        </div>
      </Card>
    </div>
  );
}
