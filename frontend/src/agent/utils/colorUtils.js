export const getScoreColor = (score) => {
  if (score < 50) return 'text-red-600 bg-red-50 border-red-200';
  if (score < 85) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-green-600 bg-green-50 border-green-200';
};

export const getProgressColor = (score) => {
  if (score < 50) return 'bg-red-500';
  if (score < 85) return 'bg-yellow-500';
  return 'bg-green-500';
};

export const getRiskFlagColor = (level) => {
  const l = level.toLowerCase();
  if (l === 'high') return 'text-red-700 bg-red-100 border-red-200';
  if (l === 'medium' || l === 'moderate') return 'text-yellow-700 bg-yellow-100 border-yellow-200';
  return 'text-green-700 bg-green-100 border-green-200';
};
