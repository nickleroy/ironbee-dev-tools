math = require("math")

-- _sizes = { 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000 }
_sizes = { 1, 2, 5, 10, 20 }
_bodies = { }
_count = 0

for size = 1,table.getn(_sizes) do
  body = ""
  for n = 1,size do
    body = body .. string.format("%d",n)
  end
  _bodies[size] = body
end

request = function()
   _count = _count + 1
   op = _count % 2
   -- headers = { ["connection"] = "keep-alive" }
   headers = { }
   if op == 1 then
     num = _count % table.getn(_sizes)
     path = string.format("/%db.html", _sizes[num+1])
     return wrk.format("GET", path)
   else
     num = _count % table.getn(_bodies)
     body = _bodies[num+1]
     headers["Content-Type"] = "application/data"
     s = wrk.format("PUT", "/foo", headers, body)
     return s
   end
end
