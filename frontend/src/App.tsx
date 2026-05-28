import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Navbar } from './components/Navbar';
import { Home } from './pages/Home';
import { MovieDetail } from './pages/MovieDetail';
import { Watchlist } from './pages/Watchlist';
import { Watched } from './pages/Watched';
import { useMovieStore } from './store/useMovieStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
});

function App() {
  const initStore = useMovieStore((s) => s.initStore);

  useEffect(() => {
    initStore();
  }, [initStore]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Navbar />
        <Routes>
          <Route path="/"           element={<Home />} />
          <Route path="/movie/:id"  element={<MovieDetail />} />
          <Route path="/watchlist"  element={<Watchlist />} />
          <Route path="/watched"    element={<Watched />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
