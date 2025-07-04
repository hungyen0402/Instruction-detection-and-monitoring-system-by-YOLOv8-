flowchart TD
    %% External Entities
    User[/"Người dùng (Học viên)"/]
    Admin[/"Quản trị viên"/]

    %% Processes
    P1[("Đặt lớp học")]
    P2[("Xem thông tin HLV")]
    P3[("Đăng nhập Admin")]
    P4[("Quản lý lớp học")]
    P5[("Quản lý người dùng")]
    P6[("Quản lý giải đấu")]
    P7[("Gửi thông báo")]
    P8[("Xem blog / thông tin")]

    %% Data Stores
    D1[[(Dữ liệu lớp học)]]
    D2[[(Dữ liệu HLV)]]
    D3[[(Tài khoản người dùng)]]
    D4[[(Dữ liệu giải đấu)]]
    D5[[(Thông báo)]]
    D6[[(Bài viết blog)]]

    %% User interactions
    User -->|đặt lịch| P1
    P1 --> D1

    User -->|xem| P2
    P2 --> D2

    User -->|đọc| P8
    P8 --> D6

    %% Admin interactions
    Admin -->|đăng nhập| P3
    P3 --> D3

    Admin -->|quản lý| P4
    P4 --> D1

    Admin -->|quản lý| P5
    P5 --> D3

    Admin -->|quản lý| P6
    P6 --> D4

    Admin -->|gửi| P7
    P7 --> D5
    D5 --> User

    %% Blog post interaction
    Admin -->|đăng blog| P8
    P8 --> D6
