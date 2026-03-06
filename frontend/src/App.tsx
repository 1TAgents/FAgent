import { Layout } from './components/Layout';
import { AuthProvider } from './context/AuthContext';

function App() {
  return (
    <AuthProvider>
      <Layout />
    </AuthProvider>
  );
}

export default App;
