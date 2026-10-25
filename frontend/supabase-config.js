import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const SUPABASE_URL = 'https://jwpmneejwyyfvfdsmcel.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_sLsBZpKNQEkUh_FKwE21IQ_XIb-t0MH';
const STORAGE_PREFERENCE_KEY = 'crisisSense_supabase_remember';

export const isSupabaseConfigured = Boolean(SUPABASE_URL);

const authStorage = {
  getItem(key) {
    const remember = localStorage.getItem(STORAGE_PREFERENCE_KEY) !== 'false';
    return (remember ? localStorage : sessionStorage).getItem(key);
  },
  setItem(key, value) {
    const remember = localStorage.getItem(STORAGE_PREFERENCE_KEY) !== 'false';
    const activeStorage = remember ? localStorage : sessionStorage;
    const inactiveStorage = remember ? sessionStorage : localStorage;
    inactiveStorage.removeItem(key);
    activeStorage.setItem(key, value);
  },
  removeItem(key) {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  }
};

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: authStorage,
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true
  }
});

export function setRememberSession(remember) {
  localStorage.setItem(STORAGE_PREFERENCE_KEY, String(remember));
}
