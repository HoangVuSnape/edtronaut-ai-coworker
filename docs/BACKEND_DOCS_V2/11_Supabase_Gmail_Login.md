# Kế Hoạch Tích Hợp Supabase & Gmail (Google) Login Chi Tiết

Tài liệu này trình bày kế hoạch chi tiết từng bước để tích hợp tính năng đăng nhập bằng Google (Gmail) thông qua Supabase cho hệ thống `edtronaut-ai-coworker`, bao gồm cả những lưu ý (Gotchas) quan trọng trong quá trình triển khai.

---

## 1. Thiết Lập Supabase Project (Database & Auth)

### 1.1 Khởi tạo Project
- [ ] Đăng nhập vào [Supabase Dashboard](https://supabase.com/dashboard).
- [ ] Tạo một project mới (chọn region gần người dùng nhất, ví dụ: Singapore để tối ưu latency).
- [ ] Lưu lại `Project URL` và `Project API Keys` (đặc biệt là `anon` key và `service_role` key).
  > **Lưu ý:** Tuyệt đối không để lộ `service_role` key ra frontend (chặng hạn đẩy lên Github). Key này có quyền qua mặt RLS (Row Level Security) và có toàn quyền Database. Chỉ dùng trên backend bảo mật.

### 1.2 Cấu hình Google OAuth
Đây là bước bắt buộc để Supabase có thể nói chuyện được với Google.
- [ ] Truy cập [Google Cloud Console](https://console.cloud.google.com/).
- [ ] Tạo mới (hoặc chọn sẵn) một project.
- [ ] Vào **APIs & Services** > **OAuth consent screen** (Màn hình đồng ý OAuth):
  - Chọn `External` (nếu ứng dụng public).
  - Khai báo thông tin App name, User support email, Developer contact email.
  - Ở màn hình "Scopes", chọn ít nhất: `.../auth/userinfo.email`, `.../auth/userinfo.profile`, `openid`.
- [ ] Vào **Credentials** > **Create Credentials** > **OAuth client ID**:
  - `Application type`: Chọn **Web application**.
  - `Authorized redirect URIs`: Dán `Callback URL` của Supabase. Bạn có thể lấy URL này tại: Supabase Dashboard -> **Authentication** -> **Providers** -> **Google**. Nó thường có dạng: `https://<project-ref>.supabase.co/auth/v1/callback`.
  - Lưu lại `Client ID` và `Client Secret`.
- [ ] Quay lại Supabase Dashboard -> **Authentication** -> **Providers** -> Bật **Google**.
  - Dán `Client ID` và `Client Secret` vừa lấy.
  - Bật "Skip nonce checks" nếu chỉ dùng ở Web.

---

## 2. Quản Lý Dữ Liệu User (Database Schema)

Supabase tự lưu thông tin xác thực (email, mật khẩu băm, provider tokens) trong schema hệ thống là `auth` (cụ thể là bảng `auth.users`).
Tuy nhiên, best practice là KHÔNG bao giờ truy vấn trực tiếp từ frontend/API bình thường vào schema `auth`. Thay vào đó, chúng ta sẽ tạo schema ở tầng `public` để chứa thông tin người dùng (Profile).

### 2.1 Tạo bảng `public.user_profiles`
- [ ] Chạy đoạn SQL sau trong SQL Editor của Supabase (hoặc qua migrations):
  ```sql
  CREATE TABLE public.user_profiles (
      id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
      email TEXT UNIQUE NOT NULL,
      full_name TEXT,
      avatar_url TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ DEFAULT NOW()
  );
  ```
  > **Chú ý:** Ta sử dụng `ON DELETE CASCADE` để đảm bảo nếu user bị xóa khỏi hệ thống auth, thông tin profile cũng tự động bị xóa.

### 2.2 Tạo Function và Trigger đồng bộ User Server-side
Thay vì bắt Frontend tự lưu dữ liệu thông tin User lên bảng `user_profiles` mỗi khi login (rất dễ dính lỗi mạng hoặc giả mạo), ta dùng Postgres Trigger bắt sự kiện Insert.

- [ ] Chạy đoạn SQL tạo Trigger:
  ```sql
  -- 1. Tạo Function
  CREATE OR REPLACE FUNCTION public.handle_new_user()
  RETURNS TRIGGER AS $$
  BEGIN
    INSERT INTO public.user_profiles (id, email, full_name, avatar_url)
    VALUES (
      new.id,
      new.email,
      new.raw_user_meta_data->>'full_name',
      new.raw_user_meta_data->>'avatar_url'
    );
    RETURN new;
  END;
  $$ LANGUAGE plpgsql SECURITY DEFINER;
  -- Lưu ý SECURITY DEFINER rất quan trọng ở đây vì nó giúp trigger chạy dưới quyền Admin (postgres role), được phép byass RLS để insert.

  -- 2. Gắn Trigger vào bảng auth.users
  CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
  ```

### 2.3 Row Level Security (RLS)
Bảo mật dữ liệu trên bảng `user_profiles`.
- [ ] Bật RLS và viết policy cho bảng `user_profiles`:
  ```sql
  ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

  -- 1. Cho phép User xem thông tin CỦA CHÍNH HỌ
  CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    USING ( auth.uid() = id );

  -- 2. Cho phép User cập nhật thông tin CỦA CHÍNH HỌ
  CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    USING ( auth.uid() = id );
  ```
  > **Lưu ý:** Bạn có thể cần thiết kế lại Rule Số 1 (Select) nếu ứng dụng của bạn cần User A nhìn thấy Profile cơ bản của User B (ví dụ list users trong dự án). Khi đó có thể chỉnh thành policy "Mọi user login đều xem được".

---

## 3. Phát Triển Frontend (React / Vite)

### 3.1 Cài đặt & Cấu hình
- [ ] Cài đặt module Supabase:
  ```bash
  npm install @supabase/supabase-js
  ```
- [ ] Thêm Environment Variables vào frontend (file `.env` hoặc `.env.local` nếu dùng Vite):
  ```env
  VITE_SUPABASE_URL=https://<project-ref>.supabase.co
  VITE_SUPABASE_ANON_KEY=<your-anon-key>
  ```
- [ ] Khởi tạo Supabase client `src/lib/supabaseClient.ts`:
  ```typescript
  import { createClient } from '@supabase/supabase-js'

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
  const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

  export const supabase = createClient(supabaseUrl, supabaseAnonKey)
  ```

### 3.2 Giao diện Login
- [ ] Tạo Component Đăng Nhập `Login.tsx`:
  ```tsx
  import { supabase } from '@/lib/supabaseClient';

  const Login = () => {
    const handleGoogleLogin = async () => {
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          queryParams: {
            access_type: 'offline', // Bắt chước flow refresh token
            prompt: 'consent',     // Bắt buộc chọn account
          },
          redirectTo: window.location.origin + '/dashboard' // Tự động trả về trang này
        }
      });
      if (error) console.error("Login lỗi:", error);
    };

    return (
      <div>
        <h1>Welcome to Edtronaut AI</h1>
        <button onClick={handleGoogleLogin}>Google Login</button>
      </div>
    );
  };
  export default Login;
  ```

### 3.3 Quản Lý Global State
- [ ] Lắng nghe thay đổi User (để biết đang login hay logout). Ở cấp cao nhất của App (`App.tsx` hoặc Context Provider):
  ```typescript
  import { useEffect, useState } from 'react';
  import { Session } from '@supabase/supabase-js';
  import { supabase } from '@/lib/supabaseClient';

  export const AuthProvider = ({ children }) => {
    const [session, setSession] = useState<Session | null>(null);

    useEffect(() => {
      // Check session đang có
      supabase.auth.getSession().then(({ data: { session } }) => {
        setSession(session);
      });

      // Lắng nghe sự kiện login/logout
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        (_event, session) => {
          setSession(session);
        }
      );

      return () => subscription.unsubscribe();
    }, []);

    // ... Return Provider ...
  }
  ```
  > **Lưu ý:** Token (JWT) và Refresh Token được Supabase Client JS tự động xử lý và lưu ở `localStorage` của trình duyệt. Nó tự động refresh mỗi khi sắp hết hạn.

---

## 4. Tích hợp với Backend Python (FastAPI / gRPC)

Supabase JS Client ở frontend khi gọi trực tiếp vào CSDL Supabase thì rất tuyệt. Nhưng nếu Frontend phải gọi lên cái Web Backend của bạn (cụ thể là FastAPI/gRPC), backend cần xác thực người dùng đó là ai.

### 4.1 Frontend gửi Token đi đâu?
- Khi gọi Fetch/Axios API từ Frontend, lấy JWT Access Token và nhét vào Header:
  ```typescript
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  await fetch('http://localhost:8000/api/secure-data', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  ```

### 4.2 Backend (FastAPI) bắt Token và Decode
Backend không lưu password hay quản lý login, nó chỉ cần tin tưởng Supabase bằng cách Decode JWT bằng `JWT Secret` của project Supabase (Lấy ở `Settings > API > JWT Secret`).

- [ ] Cài đặt package decode JWT trên Python Backend:
  ```bash
  pip install pyjwt python-jose[cryptography] fastapi
  ```

- [ ] Code ví dụ một Fast API Dependency (Gắn như Middleware):
  ```python
  from fastapi import Depends, HTTPException, Security
  from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
  import jwt # từ PyJWT
  from typing import Annotated

  security = HTTPBearer()
  # Trong file .env, lưu JWT_SECRET của thiết lập Supabase API
  SUPABASE_JWT_SECRET = "your-supabase-jwt-secret-here"
  ALGORITHM = "HS256"

  def verify_token(credentials: Annotated[HTTPAuthorizationCredentials, Security(security)]):
      token = credentials.credentials
      try:
          # Thư viện JWT sẽ kiểm tra signature. Nếu đúng secret, Payload trả về.
          payload = jwt.decode(
              token,
              SUPABASE_JWT_SECRET,
              algorithms=[ALGORITHM],
              audience="authenticated"
          )
          # payload['sub'] chính là UUID của user trong bảng auth.users
          user_id = payload.get("sub")
          if user_id is None:
              raise HTTPException(status_code=401, detail="Invalid token")
          return user_id
      except jwt.ExpiredSignatureError:
          raise HTTPException(status_code=401, detail="Token has expired")
      except jwt.InvalidTokenError as e:
          raise HTTPException(status_code=401, detail="Invalid token signature")

  @app.get("/api/secure-data")
  def get_secure_data(user_id: Annotated[str, Depends(verify_token)]):
      # Chỉ tới hàm này được nếu token hợp lệ
      return {"message": f"Hello User {user_id}, secure data here!"}
  ```

---

## 5. Những Lỗi Đáng Chú Ý (Gotchas)

1. **Localhost và Callback OAuth:** Google đôi khi rất chặt chẽ với URL Local. Trong Console của Google, bắt buộc phải liệt kê `http://localhost:5173` (hoặc port đang dùng) vào danh sách Authorized JS Origins.
2. **Missing user metadata:** Khi trigger chạy tạo `user_profiles`, Google có thể trả full_name là `full_name` hoặc `name` tùy setting Scope. Cần dùng lệnh `SELECT * FROM auth.users` trên backend Supabase để check cái cột `raw_user_meta_data` nó có shape JSON như nào để viết hàm Trigger lấy trường tên & Avatar cho đúng.
3. **Môi trường Dev và Prod**: Luôn phân tách project Supabase Development và Production. Key của Development có thể để bừa cho Dev xài, key của Production tuyệt đối không đưa linh tinh.
4. **Hết hạn Token giữa chừng (Token Expiry):** Mặc định session tồn tại ~1 giờ. Client Supabase (JS) sẽ cố renew ngầm ở dưới bằng `refresh_token`. Nhưng trong lúc gọi API (FastAPI) có khả năng dính lỗi 401 khi token vừa chết và client chưa kịp đổi thẻ. Frontend cần có logic retry (thử lại request) nếu backend báo 401 do Expired Token.
