import { useState } from 'react';
import NewDashboard from './components/NewDashboard';
import ObservatoryDashboard from './components/ObservatoryDashboard';

function App() {
  const [screen, setScreen] = useState('dashboard');

  if (screen === 'observatory') {
    return <ObservatoryDashboard onBack={() => setScreen('dashboard')} />;
  }

  return <NewDashboard onNavigate={setScreen} />;
}

export default App;
