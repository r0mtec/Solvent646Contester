#define _CRT_SECURE_NO_WARNINGS
#include <iostream>
#include <cstdio>
#include <stack>
#include <vector>
#include <iomanip>
#include <algorithm>
#include <string>
#include <cmath>
#include <queue>
#include <set>
#include <array>
#include <chrono> 
#include <map>
#include <cassert>
#include <math.h>
#include <numeric>
#include <ctime>
#include <time.h>
#include <deque>
#include <tuple>
#include <unordered_set>
#include <unordered_map>


using namespace std;


typedef long long ll;
typedef unsigned long long ull;
typedef unsigned int uint;
typedef long double ld;
typedef pair<long long, long long> pll;
typedef pair<int, int> pii;


const ll LINF = 100090009990;
const int INF = 1009000999;
const ld PI = 3.1415926535;
const ld E = 2.7182818284;
const ll MOD = 1000000007;
const int MAX = 150010;
const ld EPS = 1e-7;


bool check(int dig)
{
    long long root = static_cast<long long>(sqrt(dig));

    return root * root != dig;
}

bool is_prime(ll dig)
{
    for(int i = 2; i <= sqrt(dig); i++)
    {
        if(dig % i  == 0)
        {
            return false;
        }
    }
    return true;
}


string to_bit(ll dig)
{
    string res;
    while (dig != 0)
    {
        res += ((dig % 2) + '0');
        dig /= 2;
    }
    return res;
}

int solve(ll m) {
    if (m % 2 == 0)
    {
        return m;
    }
    else
    {
        ll otv = 0;
        string s = to_bit(m);
        for (auto& e : s)
        {
            if (e == '1') otv += m;
        }
        return otv;
    }
}

void generate_test()
{
    int m = 50;
    while (m--)
    {
        ll k = rand() % (100000000000000000);
        ll res = solve(k);
        cout << k << " " << res << endl;
    }
    ll k = 100000000000000000;
    ll res = solve(k);
    cout << k << " " << res << endl;
}




void true_solve()
{
    ll m; cin >> m;
    if (m % 2 == 0)
    {
        cout << m;
    }
    else
    {
        ll otv = 0;
        string s = to_bit(m);
        for (auto& e : s)
        {
            if (e == '1') otv += m;
        }
        cout << otv;
    }
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
#ifndef ONLINE_JUDGE
    //FILE* IN_FILE = freopen("input.txt", "r", stdin);
   // FILE* OUT_FILE = freopen("output.txt", "w", stdout);
#endif
    int t_t_t = 1;
   // cin >> t_t_t;
    while (t_t_t--) {
        //generate_test();
        true_solve();
    }

    return 0;
}