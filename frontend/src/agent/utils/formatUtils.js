export const formatPercentage = (value) => {
  return `${Math.round(value * 100)}%`;
};

export const formatStepStatus = (status) => {
  if (status === 'success') return 'text-green-400';
  if (status === 'warning') return 'text-yellow-400';
  if (status === 'error') return 'text-red-400';
  return 'text-gray-400';
};
