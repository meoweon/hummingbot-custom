import streamlit as st

from frontend.st_utils import get_backend_api_client, initialize_st_page, t

initialize_st_page(page_title=t("Credentials"), icon="🔑")

# Page content
client = get_backend_api_client()
NUM_COLUMNS = 4


@st.cache_data
def get_all_connectors_config_map():
    connectors_map = client.get_all_connectors_config_map()
    # 添加防御性代码：过滤掉非列表类型的配置映射值和"code"
    if isinstance(connectors_map, dict):
        # 移除名为"code"的项以及值不是列表类型的项
        invalid_keys = [k for k, v in connectors_map.items() if not isinstance(v, list) or k == "code"]
        for key in invalid_keys:
            connectors_map.pop(key, None)
    return connectors_map


# Section to display available accounts and credentials
accounts = client.get_accounts()
all_connector_config_map = get_all_connectors_config_map()
st.header(t("Available Accounts and Credentials"))

if accounts:
    n_accounts = len(accounts)
    accounts.remove("master_account")
    accounts.insert(0, "master_account")
    for i in range(0, n_accounts, NUM_COLUMNS):
        cols = st.columns(NUM_COLUMNS)
        for j, account in enumerate(accounts[i : i + NUM_COLUMNS]):
            with cols[j]:
                st.subheader(f"🏦  {account}")
                credentials = client.get_credentials(account)
                st.json(credentials)
else:
    st.write(t("No accounts available."))

st.markdown("---")

c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    # Section to create a new account
    st.header(t("Create a New Account"))
    new_account_name = st.text_input(t("New Account Name"))
    if st.button(t("Create Account")):
        new_account_name = new_account_name.replace(" ", "_")
        if new_account_name:
            if new_account_name in accounts:
                st.warning(t("Account {account_name} already exists.").format(account_name=new_account_name))
                st.stop()
            elif new_account_name == "" or all(char == "_" for char in new_account_name):
                st.warning(t("Please enter a valid account name."))
                st.stop()
            response = client.add_account(new_account_name)
            st.write(response)
        else:
            st.write(t("Please enter an account name."))

with c2:
    # Section to delete an existing account
    st.header(t("Delete an Account"))
    delete_account_name = st.selectbox(
        t("Select Account to Delete"),
        options=accounts if accounts else [t("No accounts available")],
    )
    if st.button(t("Delete Account")):
        if delete_account_name and delete_account_name != t("No accounts available"):
            response = client.delete_account(delete_account_name)
            st.warning(response)
        else:
            st.write(t("Please select a valid account."))

with c3:
    # Section to delete a credential from an existing account
    st.header(t("Delete Credential"))
    delete_account_cred_name = st.selectbox(
        t("Select the credentials account"),
        options=accounts if accounts else [t("No accounts available")],
    )
    creds_for_account = [credential.split(".")[0] for credential in client.get_credentials(delete_account_cred_name)]
    delete_cred_name = st.selectbox(
        t("Select a Credential to Delete"), options=creds_for_account if creds_for_account else [t("No credentials available")]
    )
    if st.button(t("Delete Credential")):
        if (delete_account_cred_name and delete_account_cred_name != t("No accounts available")) and (
            delete_cred_name and delete_cred_name != t("No credentials available")
        ):
            response = client.delete_credential(delete_account_cred_name, delete_cred_name)
            st.warning(response)
        else:
            st.write(t("Please select a valid account."))

st.markdown("---")

# Section to add credentials
st.header(t("Add Credentials"))
c1, c2 = st.columns([1, 1])
with c1:
    account_name = st.selectbox(t("Select Account"), options=accounts if accounts else [t("No accounts available")])
with c2:
    # 确保只显示有效的连接器
    all_connectors = list(all_connector_config_map.keys())
    binance_perpetual_index = all_connectors.index("binance_perpetual") if "binance_perpetual" in all_connectors else None

    if not all_connectors:
        st.error(t("No valid connectors available."))
        st.stop()

    connector_name = st.selectbox(t("Select Connector"), options=all_connectors, index=binance_perpetual_index)

    # 再次检查选定的连接器是否有有效的配置
    if connector_name not in all_connector_config_map or not isinstance(all_connector_config_map[connector_name], list):
        st.error(t("Selected connector {connector} has invalid configuration.").format(connector=connector_name))
        st.stop()

    config_map = all_connector_config_map[connector_name]

st.write(t("Configuration Map for {connector}:").format(connector=connector_name))
config_inputs = {}
cols = st.columns(NUM_COLUMNS)

# 确保config_map是可迭代的
if not isinstance(config_map, (list, tuple)):
    st.error(t("Configuration for {connector} is invalid.").format(connector=connector_name))
    st.stop()

for i, config in enumerate(config_map):
    with cols[i % (NUM_COLUMNS - 1)]:
        config_inputs[config] = st.text_input(config, type="password", key=f"{connector_name}_{config}")

with cols[-1]:
    if st.button(t("Submit Credentials")):
        response = client.add_connector_keys(account_name, connector_name, config_inputs)
        if response:
            st.success(response)
