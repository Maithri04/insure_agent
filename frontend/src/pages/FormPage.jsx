import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { generateSOAP } from '../services/api';

const FormPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    patient_name: '',
    patient_age: '',
    patient_gender: '',
    raw_notes: '',
    medications: ''
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      // Call the API service to generate SOAP
      const response = await generateSOAP({
        ...formData,
        patient_age: parseInt(formData.patient_age, 10)
      });
      
      // Navigate to SOAP page with the generated data
      navigate('/soap', { state: { soapData: response, patientData: formData } });
    } catch (error) {
      console.error('Error generating SOAP:', error);
      alert('Failed to generate SOAP report. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Patient Details</h1>
        <p className="text-gray-500 mt-2">Fill in the patient's information to generate a SOAP report.</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="col-span-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Patient Name <span className="text-red-500">*</span></label>
              <input
                type="text"
                name="patient_name"
                required
                value={formData.patient_name}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                placeholder="John Doe"
              />
            </div>
            
            <div className="col-span-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Age <span className="text-red-500">*</span></label>
              <input
                type="number"
                name="patient_age"
                required
                min="0"
                value={formData.patient_age}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                placeholder="45"
              />
            </div>

            <div className="col-span-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Gender <span className="text-red-500">*</span></label>
              <select
                name="patient_gender"
                required
                value={formData.patient_gender}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all bg-white"
              >
                <option value="" disabled>Select Gender</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Clinical Notes (Raw) <span className="text-red-500">*</span></label>
            <textarea
              name="raw_notes"
              required
              rows="5"
              value={formData.raw_notes}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all resize-y"
              placeholder="Enter doctor's raw observations and notes..."
            ></textarea>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Medications <span className="text-red-500">*</span></label>
            <textarea
              name="medications"
              required
              rows="3"
              value={formData.medications}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all resize-y"
              placeholder="List current and prescribed medications..."
            ></textarea>
          </div>

          <div className="pt-4 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className={`px-8 py-3 rounded-lg font-medium text-white transition-all shadow-md flex items-center ${
                loading ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 hover:shadow-lg'
              }`}
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Generating SOAP...
                </>
              ) : (
                'Generate SOAP Report'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FormPage;
