# Go 语法速查（Python 对照）


## 变量 & 类型

```go
// 声明
var x int = 1          // 完整写法
x := 1                 // 短声明（函数内），自动推断 int
var y string           // 默认 ""，int 默认 0，bool 默认 false

// 常量
const Pi = 3.14
```

| Go | Python |
|----|--------|
| `int` `float64` `string` `bool` | `int` `float` `str` `bool` |
| `var x int = 1` | `x: int = 1` |
| `x := 1` | `x = 1` |
| 没有 `None` | `None` |
| `nil`（指针/接口/切片/map/chan） | `None` |
| `*string` 可为 nil | `Optional[str]` |


## if / for / switch

```go
// if — 可以带初始化语句
if x > 0 {
    fmt.Println("正数")
} else if x < 0 {
    fmt.Println("负数")
} else {
    fmt.Println("零")
}

// 带初始化的 if（常见错误处理模式）
if err := doSomething(); err != nil {
    return err
}

// for — 唯一的循环关键字！没有 while
for i := 0; i < 10; i++ {   // 经典 for
    fmt.Println(i)
}

for x > 0 {                 // 等价 while x > 0
    x--
}

for {                       // 等价 while True
    break
}

for i, v := range items {   // 等价 for i, v in enumerate(items)
    fmt.Println(i, v)
}

// switch — 自动 break，不需要写
switch x {
case 1:
    fmt.Println("one")
case 2, 3:                  // 多个值
    fmt.Println("two or three")
default:
    fmt.Println("other")
}
```

| Go | Python |
|----|--------|
| `if x > 0 { }` | `if x > 0:` |
| `for i := 0; i < n; i++ { }` | `for i in range(n):` |
| `for _, v := range slice { }` | `for v in list:` |
| `for cond { }` | `while cond:` |
| `switch` 自动 break | `match` 或 `if/elif` |


## 数组 / 切片 / Map

```go
// 切片 Slice — 类似 Python list，可变长
nums := []int{1, 2, 3}
nums = append(nums, 4)           // nums = [1,2,3,4]
fmt.Println(len(nums))           // 4
sub := nums[1:3]                 // [2,3]

// 数组 Array — 固定长，很少直接用
var arr [3]int = [3]int{1, 2, 3}

// Map — 类似 Python dict，必须 make 初始化
scores := make(map[string]int)   // make 初始化
scores["alice"] = 95
v, ok := scores["bob"]           // ok=false，键不存在
if ok {
    fmt.Println(v)
}
delete(scores, "alice")          // 删除键

// 字面量初始化
m := map[string]int{"a": 1, "b": 2}
```

| Go | Python |
|----|--------|
| `[]int{1,2,3}` | `[1, 2, 3]` |
| `append(s, x)` | `list.append(x)` |
| `len(s)` | `len(l)` |
| `s[1:3]` | `l[1:3]` |
| `map[string]int` | `dict[str, int]` |


## 函数

```go
// 基本函数
func add(a int, b int) int {
    return a + b
}

// 参数类型相同可缩写
func add(a, b int) int { return a + b }

// 多返回值（Go 特色）
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("除零错误")  // nil ≈ None
    }
    return a / b, nil
}

// 调用 + 错误处理
result, err := divide(10, 2)
if err != nil {
    log.Fatal(err)
}
fmt.Println(result)

// 命名返回值
func split(sum int) (x, y int) {
    x = sum * 4 / 9
    y = sum - x
    return  // naked return，返回 x, y
}

// 可变参数
func sum(nums ...int) int {  // ... ≈ Python *args
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}
```

| Go | Python |
|----|--------|
| `func f(x int) int { }` | `def f(x: int) -> int:` |
| `return v, err` | `return v` 或 `raise` |
| `...int` | `*args` |
| 没有关键字参数 | `def f(a=1, b=2)` |


## struct & method

```go
// 定义 struct
type Paper struct {
    ID    uint    `json:"id"`
    Title *string `json:"title"`
    Year  int     `json:"year"`
}

// 创建
p := Paper{ID: 1, Year: 2025}
p2 := Paper{ID: 2, Title: strPtr("LaH10"), Year: 2025}

// method — 带接收者的函数
func (p Paper) Summary() string {  // 值接收者，不修改原 struct
    if p.Title == nil {
        return "无标题"
    }
    return *p.Title  // * 解引用指针
}

func (p *Paper) SetTitle(t string) {  // 指针接收者，修改原 struct
    p.Title = &t
}

// 调用
fmt.Println(p.Summary())    // "无标题"
p.SetTitle("hello")         // (&p).SetTitle 的简写
fmt.Println(p.Summary())    // "hello"
```

| Go | Python |
|----|--------|
| `type T struct { }` | `class T:` 或 `@dataclass` |
| `func (p Paper) M()` | `def m(self):` |
| `func (p *Paper) M()` | 修改 self 的方法 |
| 没有继承 | 继承 |
| interface 实现是隐式的 | ABC 或 duck typing |


## 指针 * 和 &

```go
x := 42
p := &x        // & 取地址，p 是 *int 类型
fmt.Println(p)  // 0xc000014098（地址）
fmt.Println(*p) // 42（解引用）

*p = 100       // 通过指针修改 x
fmt.Println(x) // 100

// 函数传指针 vs 传值
func byValue(p Paper) {
    p.Year = 2020  // 改的是副本
}

func byPointer(p *Paper) {
    p.Year = 2020  // 改的是原值
}

paper := Paper{Year: 2019}
byValue(paper)
fmt.Println(paper.Year)  // 2019 ← 没变！
byPointer(&paper)
fmt.Println(paper.Year)  // 2020 ← 变了
```

**核心**：Go 默认传值（复制），用 `*` 和 `&` 才能传引用。


## interface

```go
// 定义接口 — 是一组方法签名
type Stringer interface {
    String() string
}

// 隐式实现 — 只要 struct 有 String() 方法，就自动实现了 Stringer
func (p Paper) String() string {
    return fmt.Sprintf("Paper#%d", p.ID)
}

// 接受接口的函数
func print(s Stringer) {
    fmt.Println(s.String())
}

print(Paper{ID: 1})  // Paper 实现了 Stringer，可以直接传入
```

| Go | Python |
|----|--------|
| `interface { M() }` | `Protocol` 或 ABC |
| 隐式实现 | 显式继承/注册 |
| 接口通常很小（1-3 方法） | 通常较大 |


## error 处理（核心模式）

```go
// Go 没有 try/except。函数返回 error，调用方检查。
func readFile(path string) ([]byte, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("读取失败 %s: %w", path, err)
    }
    return data, nil
}

// 调用
data, err := readFile("config.json")
if err != nil {
    log.Fatal(err)  // 打印并退出
}
fmt.Println(string(data))

// 自定义 error
var ErrNotFound = errors.New("not found")

func find(id int) (*Paper, error) {
    if id <= 0 {
        return nil, ErrNotFound
    }
    return &Paper{ID: uint(id)}, nil
}
```

| Go | Python |
|----|--------|
| `if err != nil { return }` | `try: ... except: ...` |
| `errors.New("msg")` | `Exception("msg")` |
| `fmt.Errorf("...%w", err)` | `raise ... from err` |


## defer（类似 finally）

```go
func processFile(path string) error {
    f, err := os.Open(path)
    if err != nil {
        return err
    }
    defer f.Close()  // 函数退出时自动执行，无论正常还是 panic

    // ... 处理文件 ...
    return nil
}
```

| Go defer | Python |
|----|--------|
| `defer f.Close()` | `with open(...) as f:` |
| 任意函数末尾执行 | 固定 `__exit__` |
| 多个 defer 按后进先出 | - |


## goroutine & channel（并发核心）

```go
// goroutine — 用 go 关键字启动
func worker(id int, ch chan string) {
    time.Sleep(time.Second)
    ch <- fmt.Sprintf("worker %d done", id)  // 发送到 channel
}

ch := make(chan string)  // 创建 channel
go worker(1, ch)         // 启动 goroutine
go worker(2, ch)
result := <-ch           // 从 channel 接收（阻塞直到有数据）
fmt.Println(result)
```

| Go | Python |
|----|--------|
| `go f()` | `asyncio.create_task(f())` |
| `ch := make(chan T)` | `asyncio.Queue()` |
| `ch <- v` | `queue.put(v)` |
| `v := <-ch` | `v = await queue.get()` |
| goroutine 成本 ~2KB | asyncio 成本 ~KB |


## 常用代码片段

```go
// 字符串操作
import "strings"
strings.Contains(s, "sub")      // "sub" in s
strings.HasPrefix(s, "pre")     // s.startswith("pre")
strings.Split(s, ",")           // s.split(",")
strings.Join(parts, "-")        // "-".join(parts)
strconv.Itoa(42)                // str(42)
strconv.Atoi("42")              // int("42")

// JSON
import "encoding/json"
data, _ := json.Marshal(obj)              // json.dumps
json.Unmarshal(data, &obj)                // json.loads

// 时间
import "time"
now := time.Now()
t := time.Date(2025, 7, 22, 0, 0, 0, 0, time.UTC)

// 排序
import "sort"
sort.Ints(nums)                           // nums.sort()
sort.Slice(papers, func(i, j int) bool {
    return papers[i].Year < papers[j].Year
})
```
