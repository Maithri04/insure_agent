import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const SplashScreen = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      navigate('/login');
    }, 2000);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-blue-600">
      <h1 className="text-white text-5xl md:text-7xl font-bold tracking-wider animate-pulse">
        Insure AI
      </h1>
    </div>
  );
};

export default SplashScreen;
