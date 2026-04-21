import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/Button";
import Card from "../components/Card";
import InputField from "../components/InputField";
import SectionTitle from "../components/SectionTitle";
import { useAppState } from "../context/AppStateContext";

export default function Login() {
  const navigate = useNavigate();
  const { setDoctor } = useAppState();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    regNo: "",
  });

  const onChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const onLogin = () => {
    const doctorData = {
      name: form.name,
      email: form.email,
      regNo: form.regNo,
    };
    localStorage.setItem("doctor", JSON.stringify(doctorData));
    setDoctor(doctorData);
    navigate("/agent");
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <Card className="w-full max-w-lg">
        <SectionTitle
          title="Doctor Login"
          description="Sign in to continue with InsureMind AI hospital workflow."
        />
        <div className="space-y-4 mt-4">
          <InputField label="Doctor Name" name="name" value={form.name} onChange={onChange} />
          <InputField label="Email" name="email" type="email" value={form.email} onChange={onChange} />
          <InputField label="Password" name="password" type="password" value={form.password} onChange={onChange} />
          <InputField
            label="Registration Number"
            name="regNo"
            value={form.regNo}
            onChange={onChange}
          />
          <Button onClick={onLogin} className="w-full">
            Login
          </Button>
        </div>
      </Card>
    </div>
  );
}
