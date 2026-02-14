import { useState } from 'react';
import NewDashboard from './components/NewDashboard';
import ObservatoryDashboard from './components/ObservatoryDashboard';
import GenomeDashboard from './components/GenomeDashboard';
import CoreValuesEditor from './components/CoreValuesEditor';

function App() {
  const [screen, setScreen] = useState('dashboard');

  if (screen === 'observatory') {
    return <ObservatoryDashboard onBack={() => setScreen('dashboard')} />;
  }

  if (screen === 'genome') {
    return <GenomeDashboard onBack={() => setScreen('dashboard')} />;
  }

  if (screen === 'core-values') {
    return <CoreValuesEditor onBack={() => setScreen('dashboard')} />;
  }

  return <NewDashboard onNavigate={setScreen} />;
}

export default App;
